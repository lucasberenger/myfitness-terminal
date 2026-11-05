import io
import json
from urllib.error import HTTPError, URLError
from unittest.mock import patch
from uuid import uuid4
import pytest
from fitness_chat.cli import ChatError, interact, load_state, send_message

URL = 'http://127.0.0.1:8000'


def reader(*lines):
    iterator = iter(lines)
    return lambda _: next(iterator)


def test_session_resumes_and_renders_newlines(tmp_path):
    path = tmp_path / 'session.json'
    identifier = str(uuid4())
    output = []
    with patch('fitness_chat.cli.send_message', return_value={
        'conversation_id': identifier, 'message': 'Almoço\n260 kcal'}) as send:
        assert interact(URL, path, 45, read=reader('', 'Oi', '/exit'), write=output.append) == 0
        assert 'App > Almoço\n260 kcal' in '\n'.join(output)
        assert load_state(path)[URL] == identifier
        interact(URL, path, 45, read=reader('Total?', '/exit'), write=output.append)
        assert send.call_args.args[2] == identifier


def test_new_resets_only_current_server_and_does_not_send_commands(tmp_path):
    path = tmp_path / 'session.json'
    path.write_text(json.dumps({URL: str(uuid4()), 'http://other': str(uuid4())}))
    with patch('fitness_chat.cli.send_message') as send:
        interact(URL, path, 45, read=reader('/new', '/help', '/conversation', '/exit'), write=lambda _: None)
        send.assert_not_called()
    assert URL not in load_state(path)
    assert 'http://other' in load_state(path)


def test_network_failure_is_not_retried(tmp_path):
    with patch('fitness_chat.cli.send_message', side_effect=ChatError('Falha')) as send:
        interact(URL, tmp_path / 'session.json', 45,
                 read=reader('Registre almoço', '/exit'), write=lambda _: None)
        assert send.call_count == 1
    assert not (tmp_path / 'session.json').exists()


def test_http_payload_and_response():
    identifier = str(uuid4())
    response = io.BytesIO(json.dumps({'conversation_id': identifier, 'message': 'Uma\nlinha'}).encode())
    with patch('fitness_chat.cli.urlopen', return_value=response) as opening:
        result = send_message(URL, 'Olá', identifier, 45)
    assert result['message'] == 'Uma\nlinha'
    assert json.loads(opening.call_args.args[0].data) == {'message': 'Olá', 'conversation_id': identifier}


def test_connection_error_explains_uncertain_result():
    with patch('fitness_chat.cli.urlopen', side_effect=URLError('offline')):
        with pytest.raises(ChatError, match='pode ter sido salvo'):
            send_message(URL, 'Registre', None, 45)


def test_missing_conversation_suggests_new():
    error = HTTPError(URL, 404, 'Missing', {}, io.BytesIO(b'{"detail":"Conversa inexistente"}'))
    with patch('fitness_chat.cli.urlopen', side_effect=error):
        with pytest.raises(ChatError, match='/new'):
            send_message(URL, 'Oi', str(uuid4()), 45)


def test_invalid_state_does_not_silently_start_new_conversation(tmp_path):
    path = tmp_path / 'session.json'
    path.write_text('broken')
    with patch('fitness_chat.cli.send_message') as send:
        assert interact(URL, path, 45, write=lambda _: None) == 1
        send.assert_not_called()
