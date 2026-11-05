from datetime import date
from decimal import Decimal
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fitness_chat.persistence import Base, Food
from fitness_chat.schemas import FoodInput, MealInput
from fitness_chat.services import NotFound, daily_summary, nutrients, register_meal, require


@pytest.fixture
def session():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Food(**FoodInput(name='Arroz', source='Rótulo de teste',
                         calories=130, protein='2.5', carbs=28, fat='0.3').model_dump()))
        session.commit()
        yield session
    engine.dispose()


def meal(**changes):
    return MealInput(**({'food_id': 1, 'label': 'Almoço', 'grams': '150',
                         'consumed_at': '2026-11-04T12:00:00-03:00'} | changes))


def test_register_correct_snapshot_delete(session):
    item = register_meal(session, meal())
    assert nutrients(item)['calories'] == Decimal('195')
    session.get(Food, 1).calories = Decimal('999')
    item.grams = Decimal('200')
    session.commit()
    session.expire_all()
    assert nutrients(item)['calories'] == Decimal('260')
    result = daily_summary(session, date(2026, 11, 4), 'America/Sao_Paulo')
    assert result['totals'].calories == Decimal('260')
    session.delete(item)
    session.commit()
    assert daily_summary(session, date(2026, 11, 4), 'America/Sao_Paulo')['items'] == []


def test_day_boundaries(session):
    register_meal(session, meal(consumed_at='2026-11-05T02:59:59Z'))
    register_meal(session, meal(consumed_at='2026-11-05T03:00:00Z'))
    for day in (4, 5):
        assert len(daily_summary(session, date(2026, 11, day), 'America/Sao_Paulo')['items']) == 1


@pytest.mark.parametrize('changes', [{'grams': '-1'}, {'grams': '0'},
    {'grams': 'NaN'}, {'consumed_at': '2026-11-05T03:00:00'}])
def test_invalid_meal(changes):
    with pytest.raises(ValidationError):
        meal(**changes)


def test_missing_food_does_not_register(session):
    with pytest.raises(NotFound):
        register_meal(session, meal(food_id=999))
    assert daily_summary(session, date(2026, 11, 4), 'America/Sao_Paulo')['items'] == []
