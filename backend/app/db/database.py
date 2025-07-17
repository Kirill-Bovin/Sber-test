import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()  # Загружаем переменные окружения из .env файла

DATABASE_URL = os.getenv("DATABASE_URL")  # Получаем строку подключения к БД

# Создаём асинхронный движок SQLAlchemy с выводом SQL-запросов (echo=True)
engine = create_async_engine(DATABASE_URL, echo=True)

# Создаём асинхронный сессионный класс, который будет создавать сессии для работы с БД
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_session() -> AsyncSession:
    """
    Асинхронный генератор сессий для работы с базой данных.

    Используется, например, в FastAPI для dependency injection.
    """
    async with async_session() as session:
        yield session