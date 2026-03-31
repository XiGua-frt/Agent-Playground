"""
RAG检索模块
"""
from typing import List, Tuple, Optional
from langchain_core.documents import Document
from src.data.vector_store import VectorStore
from src.config.settings import settings
from src.config.prompts import format_rag_context


class Retriever:
    """RAG检索器"""

    def __init__(self, vector_store: Optional[VectorStore] = None):
        """
        初始化检索器

        Args:
            vector_store: 向量存储实例，如为None则创建新的
        """
        self.vector_store = vector_store or VectorStore()

    def retrieve(
        self,
        query: str,
        top_k: int = None,
        score_threshold: float = None
    ) -> List[Tuple[Document, float]]:
        """
        检索相关文档

        Args:
            query: 查询文本
            top_k: 返回结果数量
            score_threshold: 分数阈值

        Returns:
            文档和相似度分数的列表
        """
        return self.vector_store.query(
            query_text=query,
            top_k=top_k,
            score_threshold=score_threshold
        )

    def retrieve_with_context(
        self,
        query: str,
        top_k: int = None,
        score_threshold: float = None
    ) -> str:
        """
        检索并返回格式化上下文

        Args:
            query: 查询文本
            top_k: 返回结果数量
            score_threshold: 分数阈值

        Returns:
            格式化后的上下文字符串
        """
        results = self.retrieve(query, top_k, score_threshold)
        return format_rag_context(results)

    def get_relevance_stats(self, query: str) -> dict:
        """
        获取检索相关性统计

        Args:
            query: 查询文本

        Returns:
            统计信息字典
        """
        # 先获取未过滤的结果
        raw_results = self.vector_store.query(
            query_text=query,
            top_k=settings.query_top_k * 2,  # 获取更多结果用于统计
            score_threshold=1.0  # 不过滤
        )

        if not raw_results:
            return {
                "total_found": 0,
                "relevant_count": 0,
                "avg_score": 0,
                "min_score": 0,
                "max_score": 0
            }

        # 计算过滤后的结果
        filtered_results = [
            (doc, score) for doc, score in raw_results
            if score < settings.similarity_threshold
        ]

        # 计算统计信息
        scores = [score for _, score in raw_results]
        return {
            "total_found": len(raw_results),
            "relevant_count": len(filtered_results),
            "avg_score": sum(scores) / len(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "threshold": settings.similarity_threshold
        }

    def format_results(self, results: List[Tuple[Document, float]]) -> str:
        """格式化检索结果（向后兼容）"""
        return format_rag_context(results)