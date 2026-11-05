# Fitness Chat

Diário alimentar pessoal: Python, uv, FastAPI, PostgreSQL e agente Groq.

## Executar localmente

```sh
uv sync
# Crie .env a partir de .env.example apenas se ainda não existir.
docker compose up -d db
uv run alembic upgrade head
uv run uvicorn fitness_chat.api:app --reload --host 127.0.0.1
```

O Compose oferece um banco local com credenciais de desenvolvimento iguais às
indicadas em `.env.example`. Se você já usa outro banco, configure `DATABASE_URL`
e dispense o Compose. As migrações são explícitas; a API não cria tabelas no startup.

Swagger: http://127.0.0.1:8000/docs. `/health` verifica apenas o processo HTTP.
API local de usuário único, ainda sem autenticação.

## Funcionalidades implementadas

- `POST /foods`: cadastrar nome, fonte e nutrientes por 100 g.
- `GET /foods?q=arroz`: buscar no catálogo (até 100 resultados por chamada).
- `POST /meal-items`: registrar alimento, gramas, identificação da refeição e horário.
- `PATCH /meal-items/{id}`: corrigir a quantidade em gramas.
- `DELETE /meal-items/{id}`: excluir o registro.
- `GET /summaries/daily?day=2026-11-04`: consultar itens e totais do dia.

Exemplo de alimento (valores apenas ilustrativos):

```json
{"name":"Arroz de teste","source":"Exemplo didático","calories":130,"protein":2.5,"carbs":28,"fat":0.3}
```

Exemplo de registro (substitua `food_id` pelo ID retornado):

```json
{"food_id":1,"label":"Almoço","grams":150,"consumed_at":"2026-11-04T12:00:00-03:00"}
```

Horários devem incluir fuso. O resumo usa `TIMEZONE` (padrão
`America/Sao_Paulo`). Os nutrientes por 100 g, o nome e a fonte são copiados
para cada registro, preservando o histórico se o catálogo mudar.
Cálculos usam Decimal; decimais são serializados como strings na resposta.

## Verificar e desenvolver

```sh
uv run pytest -q
uv run alembic check
uv run alembic revision --autogenerate -m "descricao"
```

Os testes atuais exercitam serviços e validação com SQLite em memória, incluindo
correções, snapshots e fronteiras de dia. Não substituem testes HTTP e PostgreSQL.
A migração inicial também é verificada em SQLite isolado no ambiente de desenvolvimento.

Dependências: `uv add pacote`, `uv add --dev pacote`. Versione `uv.lock`.
Nunca versione `.env`.

## Chat com Groq

Aplique a nova migração e reinicie a API:

```sh
uv run alembic upgrade head
uv run uvicorn fitness_chat.api:app --reload --host 127.0.0.1
```

Configure `GROQ_API_KEY` e `GROQ_MODEL` no `.env`.
Exemplo de modelo: `llama-3.3-70b-versatile`. Ele deve estar disponível na sua
conta e suportar tool calling. O SDK é síncrono, assim como os serviços SQL;
o endpoint FastAPI executa no pool de threads.

No Swagger, use `POST /chat`:

```json
{"message":"Quais alimentos com arroz estão cadastrados?"}
```

A resposta contém `message` e `conversation_id`. Reutilize o identificador nas
mensagens seguintes para manter o contexto:

```json
{"message":"Registre 150 g desse arroz no almoço de hoje.","conversation_id":"UUID retornado anteriormente"}
```

Para iniciar outra conversa, omita o identificador. Conversas desconhecidas
retornam 404. O agente pode buscar alimentos, registrar e corrigir itens e
consultar resumos; exclusão e cadastro de alimentos continuam pela API comum.

O histórico fica no PostgreSQL; mensagens e resultados de ferramentas são
reenviados à Groq para fornecer contexto. Evite dados pessoais desnecessários.
Cada interação tem até `AGENT_MAX_ROUNDS` chamadas ao modelo (padrão 6), no máximo
8 ferramentas por resposta e prazo de `AGENT_TIMEOUT_SECONDS` (padrão 30).
Após 160 mensagens internas é necessário iniciar uma nova conversa.
Falhas no provedor retornam 503; limites de execução retornam 504.

Gravações e histórico da mensagem são confirmados juntos após a resposta final.
Em falhas antes do commit, as alterações são desfeitas. Não há idempotência entre
requisições: reenviar uma mensagem concluída pode duplicar o registro.
O histórico de uma mesma conversa é serializado por lock de linha no PostgreSQL.

Logs registram duração, rodada e consumo total de tokens por chamada, sem chave
ou conteúdo das mensagens. Os testes do agente simulam a Groq e não gastam tokens.
A integração real com o modelo deve ser verificada no ambiente local.

Referências: [tool calling](https://console.groq.com/docs/tool-use/local-tool-calling)
e [modelos Groq](https://console.groq.com/docs/models).

## Próximos marcos

1. Validar API e migrações com PostgreSQL local.
2. Avaliar a integração real com Groq e ampliar os cenários de avaliação.
3. Implementar CLI HTTP e conversas persistidas.
4. Adicionar idempotência, metas e avaliações do agente.

`GROQ_API_KEY` e `GROQ_MODEL` ficam no `.env`.
O comando `fitness-chat` permanece um placeholder até a implementação da CLI.
