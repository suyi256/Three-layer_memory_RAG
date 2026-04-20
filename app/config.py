"""
全局配置：从环境变量 / .env 加载，供数据库 URI、检索参数、模型名等使用。

说明：
- 字段名对应环境变量为 UPPER_SNAKE_CASE（pydantic-settings 默认行为）；
- `get_settings()` 使用 lru_cache，避免重复解析 .env。
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用级可调参数集中定义。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "RAG_mul"
    debug: bool = False

    # ---------- MySQL：业务真相源（文档注册、用户画像等）----------
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "rag"
    mysql_password: str = "ragpass"
    mysql_database: str = "rag_db"

    # ---------- Elasticsearch：词法检索（BM25），索引名需与 init 脚本一致 ----------
    es_url: str = "http://127.0.0.1:9200"
    es_index: str = "rag_chunks"

    # ---------- Chroma：向量检索；collection 与 ES 索引逻辑上一一对应 chunk ----------
    chroma_host: str = "127.0.0.1"
    chroma_port: int = 8000
    chroma_collection: str = "rag_chunks"

    # ---------- OpenAI 兼容接口：嵌入 + 对话 ----------
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"

    # ---------- 分块与混合检索 ----------
    chunk_max_chars: int = 800  # 单块最大字符数（中文场景下近似控制上下文粒度）
    chunk_overlap: int = 120  # 滑动窗口重叠，减轻边界截断导致的语义丢失
    retrieve_k_vector: int = 40  # Chroma 返回候选数，略大有利于 RRF
    retrieve_k_lexical: int = 40  # ES 返回候选数
    rrf_k: int = 60  # RRF 平滑常数 k，常用 60
    fusion_top_n: int = 16  # 融合后保留的 chunk 数上限
    context_top_n: int = 10  # 实际送入 LLM 证据条数上限（控制 token）

    default_user_id: str = "default"

    @property
    def sqlalchemy_database_uri(self) -> str:
        """SQLAlchemy 同步驱动连接串（PyMySQL）。"""
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )


@lru_cache
def get_settings() -> Settings:
    """进程内单例配置；测试时需 clear 缓存可调用 get_settings.cache_clear()。"""
    return Settings()
