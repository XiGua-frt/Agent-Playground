"""
RAG初始化模块
"""
import sys
from pathlib import Path
from typing import Optional
from langchain_community.vectorstores import Chroma
from chromadb import PersistentClient

from src.data.sample_loader import SampleLoader
from src.data.vector_store import VectorStore
from src.rag.embedder import Embedder
from src.config.settings import settings


class RAGInitializer:
    """RAG系统初始化器"""

    def __init__(self):
        """初始化"""
        self.sample_loader = SampleLoader()
        self.embedder = Embedder()

    def initialize(self, force_recreate: bool = False) -> bool:
        """
        初始化RAG系统

        Args:
            force_recreate: 是否强制重新创建向量数据库

        Returns:
            是否成功
        """
        try:
            print("🚀 开始初始化RAG系统...")

            # 1. 检查API Key
            if not settings.dashscope_api_key:
                print("❌ 请先在 .env 中设置 DASHSCOPE_API_KEY")
                return False

            # 2. 加载样本数据
            print("📂 加载爆款样本数据...")
            documents = self.sample_loader.load_samples()
            if not documents:
                print(f"⚠️ 在 {settings.viral_samples_path} 中没有找到有效的 .txt 文件")
                return False
            print(f"✅ 成功加载 {len(documents)} 篇爆款文案")

            # 3. 检查是否需要重新创建
            if force_recreate:
                print("🔄 强制重新创建向量数据库...")
                self._recreate_collection()
            else:
                # 检查集合是否已存在
                if self._collection_exists():
                    print("ℹ️  向量数据库已存在，跳过初始化")
                    return True

            # 4. 初始化向量数据库
            print("🧠 正在向量化文案内容...")
            vector_store = VectorStore.from_documents(
                documents=documents,
                embedder=self.embedder
            )

            # 5. 验证初始化结果
            collection_info = vector_store.get_collection_info()
            print(f"✅ RAG系统初始化成功！")
            print(f"   表名: {collection_info['name']}")
            print(f"   文档数: {collection_info['count']}")
            print(f"   存储位置: {settings.vector_storage_path}")

            return True

        except Exception as e:
            print(f"❌ RAG初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _collection_exists(self) -> bool:
        """检查集合是否已存在"""
        try:
            client = PersistentClient(path=settings.vector_storage_path)
            collections = client.list_collections()
            return any(col.name == settings.collection_name for col in collections)
        except Exception:
            return False

    def _recreate_collection(self):
        """重新创建集合"""
        try:
            # 删除现有集合
            vector_store = VectorStore()
            vector_store.delete_collection()
            print("🗑️  已删除现有集合")
        except Exception as e:
            print(f"⚠️ 删除集合时出错（可能不存在）: {e}")

    def check_health(self) -> dict:
        """
        检查RAG系统健康状态

        Returns:
            健康状态字典
        """
        try:
            # 检查样本目录
            sample_count = self.sample_loader.get_sample_count()

            # 检查向量数据库
            collection_exists = self._collection_exists()

            # 检查API Key
            api_key_valid = bool(settings.dashscope_api_key)

            return {
                "status": "healthy" if all([sample_count > 0, collection_exists, api_key_valid]) else "unhealthy",
                "sample_count": sample_count,
                "collection_exists": collection_exists,
                "api_key_valid": api_key_valid,
                "vector_storage_path": settings.vector_storage_path,
                "viral_samples_path": settings.viral_samples_path
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def add_samples_from_dir(self, source_dir: str) -> int:
        """
        从目录添加样本到向量数据库

        Args:
            source_dir: 源目录路径

        Returns:
            添加的样本数量
        """
        try:
            # 临时加载器
            temp_loader = SampleLoader(source_dir)
            new_documents = temp_loader.load_samples()

            if not new_documents:
                print(f"⚠️ 在 {source_dir} 中没有找到有效的 .txt 文件")
                return 0

            # 添加到向量数据库
            vector_store = VectorStore()
            vector_store.add_documents(new_documents)

            print(f"✅ 成功添加 {len(new_documents)} 篇新文案")
            return len(new_documents)

        except Exception as e:
            print(f"❌ 添加样本失败: {e}")
            return 0


def main():
    """命令行入口点"""
    import argparse

    parser = argparse.ArgumentParser(description="RAG系统初始化工具")
    parser.add_argument("--force", action="store_true", help="强制重新创建向量数据库")
    parser.add_argument("--check", action="store_true", help="检查系统健康状态")
    parser.add_argument("--add-dir", type=str, help="从指定目录添加样本")

    args = parser.parse_args()

    initializer = RAGInitializer()

    if args.check:
        # 检查健康状态
        health = initializer.check_health()
        print("\n🔍 RAG系统健康检查:")
        for key, value in health.items():
            print(f"  {key}: {value}")
        return

    if args.add_dir:
        # 添加样本
        count = initializer.add_samples_from_dir(args.add_dir)
        print(f"\n📥 添加了 {count} 个新样本")
        return

    # 初始化
    success = initializer.initialize(force_recreate=args.force)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()