from sqlalchemy import Column, Integer, String, DateTime, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from datetime import datetime

DATABASE_URL = "sqlite+aiosqlite:///lavita.db"  # Используем SQLite для простоты

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_code = Column(String, unique=True, index=True)
    username = Column(String)
    full_name = Column(String)
    phone_number = Column(String)
    address = Column(String)
    language = Column(String, default="ru")
    total_spent = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    user_code = Column(String)
    bottles_count = Column(Integer)
    location = Column(String)  # Форматированный адрес
    latitude = Column(Float)
    longitude = Column(Float)
    address_details = Column(JSON)  # Детализированные данные Nominatim
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    total_cost = Column(Float)
    delivery_notes = Column(String, nullable=True)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)