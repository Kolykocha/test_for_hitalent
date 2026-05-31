import inspect
import json
from contextlib import asynccontextmanager
from uuid import uuid4
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
import config as config_app


_is_pgbouncer = "pgbouncer" in str(config_app.DB_HOST).lower()
_dsn_suffix = "?prepared_statement_cache_size=0" if _is_pgbouncer else ""
SQLALCHEMY_DATABASE_URL = (
    f"postgresql+asyncpg://{config_app.DB_USER}:{config_app.DB_PASS}"
    f"@{config_app.DB_HOST}:{config_app.DB_PORT}/{config_app.DB_NAME}{_dsn_suffix}"
)
ASYNC_CONNECT_ARGS = (
    {
        "statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4().hex}__",
    }
    if _is_pgbouncer
    else {}
)

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,
    poolclass=NullPool,
    connect_args=ASYNC_CONNECT_ARGS,
    json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
)


SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False
)


async def get_db():
    async with SessionLocal() as session:
        yield session


@asynccontextmanager
async def get_db_context():
    async with SessionLocal() as session:
        yield session


async def run_db_task(task_fn, *args, **kwargs):
    async with SessionLocal() as session:
        async with session.begin():
            if inspect.iscoroutinefunction(task_fn):
                return await task_fn(session, *args, **kwargs)
            else:
                return await session.run_sync(lambda sync_sess: task_fn(sync_sess, *args, **kwargs))