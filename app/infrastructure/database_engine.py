from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.infrastructure.config import get_settings

settings = get_settings()

# The connection to the dabatase engine is established.
# The echo parameter tells the Engine program to log all the SQL it emits 
# to a Python logger that it will write to standard output.
engine = create_async_engine(
    settings.async_database_url,
    echo=settings.debug,
    pool_pre_ping=True
)

# A session factory is created
AsyncSessionLocal = async_sessionmaker(
    # Binds the Session to the engine, which manages database connections.
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    # Prevents SQLAlchemy from automatically flushing pending changes
    # before executing queries.
    autoflush=False
)