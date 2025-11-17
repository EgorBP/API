from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from environs import Env


env = Env()
env.read_env()

DATABASE_URL = env('DATABASE_URL')

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(bind=engine)


async def get_db():
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()
