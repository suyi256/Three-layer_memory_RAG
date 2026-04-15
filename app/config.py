from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "RAG_mul"
    debug: bool = False

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "rag"
    mysql_password: str = "ragpass"
    mysql_database: str = "rag_db"

    es_url: str = "http://127.0.0.1:9200"
    es_index: str = "rag_chunks"

    chroma_host: str = "127.0.0.1"
    chroma_port: int = 8000
    chroma_collection: str = "rag_chunks"

    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"

    chunk_max_chars: int = 800
    chunk_overlap: int = 120
    retrieve_k_vector: int = 40
    retrieve_k_lexical: int = 40
    rrf_k: int = 60
    fusion_top_n: int = 16
    context_top_n: int = 10

    default_user_id: str = "default"

    @property
    def sqlalchemy_database_uri(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
