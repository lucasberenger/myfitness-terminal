from unittest.mock import Mock
from decimal import Decimal
import pytest
from groq.types.chat import ChatCompletion
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from fitness_chat.agent.runner import AgentLimit, ChatInput, run_chat
from fitness_chat.config import Settings
from fitness_chat.persistence import Base, Conversation, Food, MealItem


def completion(content=None, calls=None):
    return ChatCompletion(id='test', created=0, model='test', object='chat.completion',
        choices=[{'index': 0, 'finish_reason': 'tool_calls' if calls else 'stop',
                  'message': {'role': 'assistant', 'content': content, 'tool_calls': calls}}])


def tool(name, arguments, identifier='call1'):
    return {'id': identifier, 'type': 'function',
            'function': {'name': name, 'arguments': arguments}}


@pytest.fixture
def session():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Food(name='Arroz', source='Teste', calories=130, protein=2,
                         carbs=28, fat=0))
        session.commit()
        yield session
    engine.dispose()


def settings(**changes):
    return Settings(_env_file=None, database_url='sqlite://', groq_api_key='test-only',
                    groq_model='test', **changes)


def test_tools_and_persisted_context(session):
    client = Mock()
    client.chat.completions.create.side_effect = [
        completion(calls=[tool('search_foods', '{"query":"arroz"}')]),
        completion(calls=[tool('create_meal', '{"food_id":1,"label":"Almoço","grams":150,"consumed_at":"2026-11-04T12:00:00-03:00"}', 'call2')]),
        completion('Registrado.'), completion('Como posso ajudar?')]
    first = run_chat(session, settings(), ChatInput(message='Registre meu almoço'), client=client)
    item = session.scalar(select(MealItem))
    assert item.grams == Decimal('150')
    run_chat(session, settings(), ChatInput(message='Obrigado', conversation_id=first.conversation_id), client=client)
    conversation = session.get(Conversation, str(first.conversation_id))
    assert conversation.messages[0]['content'] == 'Registre meu almoço'
    assert conversation.messages[-2]['content'] == 'Obrigado'
    assert len(client.chat.completions.create.call_args.kwargs['messages']) == 9


def test_limit_rolls_back_writes_and_history(session):
    client = Mock()
    client.chat.completions.create.return_value = completion(calls=[tool('create_meal',
        '{"food_id":1,"label":"Almoço","grams":150,"consumed_at":"2026-11-04T12:00:00Z"}')])
    with pytest.raises(AgentLimit):
        run_chat(session, settings(agent_max_rounds=1), ChatInput(message='Registre'), client=client)
    assert session.scalar(select(MealItem)) is None
    assert session.scalar(select(Conversation)) is None


def test_invalid_tool_arguments_return_error_to_model(session):
    client = Mock()
    client.chat.completions.create.side_effect = [
        completion(calls=[tool('create_meal', '{"grams":-10}')]),
        completion('Qual alimento e quantidade?')]
    run_chat(session, settings(), ChatInput(message='Comi arroz'), client=client)
    messages = client.chat.completions.create.call_args.kwargs['messages']
    assert 'Argumentos inválidos' in messages[-2]['content']
    assert session.scalar(select(MealItem)) is None


def test_update_uses_existing_item_id(session):
    from fitness_chat.agent.tools import execute
    from fitness_chat.schemas import MealInput
    from fitness_chat.services import register_meal
    item = register_meal(session, MealInput(food_id=1, label='Almoço', grams=150,
                         consumed_at='2026-11-04T12:00:00Z'))
    result = execute(session, 'update_meal_item',
                     f'{{"item_id":{item.id},"grams":200}}', 'America/Sao_Paulo')
    assert result.nutrients.calories == Decimal('260')
    assert execute(session, 'unknown', '{}', 'America/Sao_Paulo')['error']


def test_missing_conversation(session):
    from uuid import uuid4
    from fitness_chat.services import NotFound
    client = Mock()
    with pytest.raises(NotFound):
        run_chat(session, settings(), ChatInput(message='Oi', conversation_id=uuid4()), client=client)
    client.chat.completions.create.assert_not_called()


def test_provider_error_rolls_back(session):
    import httpx
    from groq import APIConnectionError
    from fitness_chat.agent.runner import AgentUnavailable
    client = Mock()
    client.chat.completions.create.side_effect = [completion(calls=[tool('create_meal',
        '{"food_id":1,"label":"Almoço","grams":150,"consumed_at":"2026-11-04T12:00:00Z"}')]),
        APIConnectionError(request=httpx.Request('POST', 'https://api.groq.com'))]
    with pytest.raises(AgentUnavailable):
        run_chat(session, settings(), ChatInput(message='Registre almoço'), client=client)
    assert session.scalar(select(MealItem)) is None
    assert session.scalar(select(Conversation)) is None
