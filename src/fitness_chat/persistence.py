from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Numeric, String, JSON, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from fitness_chat.config import get_settings
from functools import lru_cache


class Base(DeclarativeBase):
    pass


class Food(Base):
    __tablename__ = 'foods'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(500))
    calories: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    protein: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    carbs: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    fat: Mapped[Decimal] = mapped_column(Numeric(12, 4))


class MealItem(Base):
    __tablename__ = 'meal_items'
    id: Mapped[int] = mapped_column(primary_key=True)
    food_id: Mapped[int] = mapped_column(ForeignKey('foods.id'))
    label: Mapped[str] = mapped_column(String(100))
    consumed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    grams: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    # Valores por 100 g preservados para permitir recálculo após alterações no catálogo.
    calories: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    protein: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    carbs: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    fat: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    food_name: Mapped[str] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(500))


@lru_cache
def session_factory():
    return sessionmaker(create_engine(get_settings().database_url, pool_pre_ping=True))


def get_session():
    with session_factory()() as session:
        yield session


class Conversation(Base):
    __tablename__ = 'conversations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    messages: Mapped[list] = mapped_column(JSON, default=list)
