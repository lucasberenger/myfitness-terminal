# Fitness Chat

Diário alimentar pessoal: Python, uv, FastAPI, PostgreSQL e futuro agente Groq.

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

## Próximos marcos

1. Validar API e migrações com PostgreSQL local.
2. Integrar Groq com ferramentas validadas e ciclo de execução limitado.
3. Implementar CLI HTTP e conversas persistidas.
4. Adicionar idempotência, metas e avaliações do agente.

`GROQ_API_KEY` e `GROQ_MODEL` ficam no `.env`; ainda não são usados.
O comando `fitness-chat` permanece um placeholder até a implementação da CLI.
