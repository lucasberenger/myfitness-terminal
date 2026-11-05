"""Cliente de terminal; usa apenas HTTP, sem acesso ao banco ou à chave Groq."""
import argparse
import json
import os
from pathlib import Path
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from uuid import UUID


class ChatError(Exception):
    pass


def api_url(value: str) -> str:
    parts = urlsplit(value)
    if (parts.scheme not in ('http', 'https') or not parts.hostname
            or parts.username or parts.password or parts.query or parts.fragment):
        raise argparse.ArgumentTypeError('Informe uma URL HTTP(S) sem credenciais, query ou fragmento.')
    return value.rstrip('/')


def positive_timeout(value: str) -> float:
    import math
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError('O timeout deve ser positivo e finito.')
    return number


def load_state(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
        if not isinstance(value, dict):
            raise ValueError
        return {str(url): str(UUID(identifier)) for url, identifier in value.items()}
    except FileNotFoundError:
        return {}
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        raise ChatError('Não foi possível ler o arquivo de sessão. Use --state-file com outro caminho.') from exc


def save_state(path: Path, state: dict) -> None:
    """Substituição atômica para não deixar JSON parcial após interrupção."""
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as file:
            temporary = file.name
            json.dump(state, file)
        os.replace(temporary, path)
    except OSError as exc:
        raise ChatError('Não foi possível salvar o identificador da conversa.') from exc
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def send_message(url: str, message: str, conversation_id: str | None, timeout: float) -> dict:
    payload = {'message': message}
    if conversation_id:
        payload['conversation_id'] = conversation_id
    request = Request(url + '/chat', data=json.dumps(payload).encode(),
                      headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urlopen(request, timeout=timeout) as response:
            result = json.load(response)
        if not isinstance(result, dict) or not isinstance(result.get('message'), str):
            raise ValueError
        result['conversation_id'] = str(UUID(result['conversation_id']))
        return result
    except HTTPError as exc:
        detail = ''
        try:
            body = json.loads(exc.read())
            if isinstance(body, dict) and isinstance(body.get('detail'), str):
                detail = ': ' + body['detail']
        except (ValueError, OSError):
            pass
        finally:
            exc.close()
        hint = ' Use /new para iniciar outra conversa.' if exc.code == 404 else ''
        raise ChatError(f'API retornou HTTP {exc.code}{detail}.{hint}') from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise ChatError('Falha de conexão ou timeout. Confira se a API está ativa. '
                        'O resultado pode ter sido salvo; consulte o resumo antes de reenviar.') from exc
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise ChatError('Resposta inválida da API. Consulte o resumo antes de reenviar.') from exc


HELP = '/new: nova conversa | /conversation: mostrar ID | /help: ajuda | /exit: sair'


def interact(url: str, state_file: Path, timeout: float, *, conversation_id: str | None = None,
             new: bool = False, read=input, write=print) -> int:
    try:
        state = load_state(state_file)
        current = conversation_id or (None if new else state.get(url))
        if new:
            state.pop(url, None)
            save_state(state_file, state)
    except ChatError as exc:
        write(str(exc))
        return 1
    write('Fitness Chat — ' + url)
    write(HELP)
    if current:
        write('Continuando conversa: ' + current)
    while True:
        try:
            message = read('Você > ').strip()
            if not message:
                continue
            if message in ('/exit', '/quit'):
                return 0
            if message == '/help':
                write(HELP)
                continue
            if message == '/conversation':
                write(current or 'Nenhuma conversa iniciada.')
                continue
            if message == '/new':
                updated = dict(state)
                updated.pop(url, None)
                save_state(state_file, updated)
                state, current = updated, None
                write('Nova conversa. As refeições e o histórico anterior permanecem no servidor.')
                continue
            if message.startswith('/'):
                write('Comando desconhecido. ' + HELP)
                continue
            write('Aguardando resposta...')
            result = send_message(url, message, current, timeout)
            current = result['conversation_id']
            write('\nApp > ' + result['message'] + '\n')
            state[url] = current
            try:
                save_state(state_file, state)
            except ChatError as exc:
                write(f'{exc} Para retomar, use --conversation {current}')
        except ChatError as exc:
            write(str(exc))
        except (EOFError, KeyboardInterrupt):
            write('\nSessão encerrada. Se interrompeu uma requisição, confira o resumo antes de reenviar.')
            return 0


def main() -> int:
    parser = argparse.ArgumentParser(description='Diário alimentar pelo terminal.')
    parser.add_argument('--api-url', type=api_url, default='http://127.0.0.1:8000')
    parser.add_argument('--state-file', type=Path, default=Path('.fitness-chat.json'))
    parser.add_argument('--timeout', type=positive_timeout, default=45.0)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--conversation', type=UUID, help='Retomar uma conversa pelo UUID.')
    group.add_argument('--new', action='store_true', help='Começar sem retomar a conversa salva.')
    args = parser.parse_args()
    return interact(args.api_url, args.state_file, args.timeout, new=args.new,
                    conversation_id=str(args.conversation) if args.conversation else None)
