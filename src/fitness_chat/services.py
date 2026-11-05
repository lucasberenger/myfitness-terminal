from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
from sqlalchemy import select
from sqlalchemy.orm import Session
from fitness_chat.persistence import Food, MealItem
from fitness_chat.schemas import MealInput, MealOutput, Nutrients

NUTRIENTS = ('calories', 'protein', 'carbs', 'fat')


class NotFound(Exception):
    pass


def require(session: Session, model, identifier: int):
    item = session.get(model, identifier)
    if item is None:
        raise NotFound('Registro não encontrado')
    return item


def register_meal(session: Session, data: MealInput) -> MealItem:
    food = require(session, Food, data.food_id)
    item = MealItem(**data.model_dump(exclude={'consumed_at'}),
                    consumed_at=data.consumed_at.astimezone(timezone.utc),
                    recorded_at=datetime.now(timezone.utc), food_name=food.name,
                    source=food.source, **{n: getattr(food, n) for n in NUTRIENTS})
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def nutrients(item: MealItem) -> dict[str, Decimal]:
    return {n: getattr(item, n) * item.grams / Decimal(100) for n in NUTRIENTS}


def meal_output(item: MealItem) -> MealOutput:
    return MealOutput(**{n: getattr(item, n) for n in (
        'id', 'food_id', 'food_name', 'source', 'label', 'grams', 'consumed_at', 'recorded_at')},
        nutrients=Nutrients(**nutrients(item)))


def daily_summary(session: Session, day: date, timezone_name: str):
    zone = ZoneInfo(timezone_name)
    start = datetime.combine(day, time.min, zone).astimezone(timezone.utc)
    end = datetime.combine(day + timedelta(days=1), time.min, zone).astimezone(timezone.utc)
    items = session.scalars(select(MealItem).where(
        MealItem.consumed_at >= start, MealItem.consumed_at < end
    ).order_by(MealItem.consumed_at, MealItem.id)).all()
    totals = {n: sum((nutrients(i)[n] for i in items), Decimal(0)) for n in NUTRIENTS}
    return {'date': day, 'timezone': timezone_name,
            'items': [meal_output(i) for i in items], 'totals': Nutrients(**totals)}
