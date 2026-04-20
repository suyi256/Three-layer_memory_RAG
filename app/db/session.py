"""
SQLAlchemy 引擎与会话工厂。

- `pool_pre_ping`：连接池取出连接前 ping，避免 MySQL 断连后首次查询失败；
- `echo`：debug 时打印 SQL，便于排障。
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings

settings = get_settings()
engine = create_engine(
    settings.sqlalchemy_database_uri,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.debug,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
