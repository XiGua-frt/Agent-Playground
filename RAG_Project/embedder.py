"""
嵌入模型封装模块
"""
from typing import List, Optional
from langchain_community.embeddings import DashScopeEmbeddings
from src.config.settings import settings



class Embedder:
    """嵌入模型封装类"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        初始化嵌入模型

        Args:
            api_key: DashScope API Key，如为None则使用配置中的
            model: 嵌入模型名称，如为None则使用配置中的
        """
        self.api_key = api_key or settings.dashscope_api_key
        self.model = model or settings.embedding_model

        if not self.api_key:
            raise ValueError("DashScope API Key未配置，请设置DASHSCOPE_API_KEY环境变量")

        self.embeddings = DashScopeEmbeddings(
            model=self.model,
            dashscope_api_key=self.api_key
        )

    def embed_text(self, text: str) -> List[float]:
        """嵌入单个文本"""
        return self.embeddings.embed_query(text)

    def embed_texts(self, texts: List[str], batch_size: int = 25) -> List[List[float]]:
        """嵌入多个文本，支持分批处理避免限流"""
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            results.extend(self.embeddings.embed_documents(batch))
        return results

    def get_embedding_function(self):
        """获取LangChain嵌入函数"""
        return self.embeddings