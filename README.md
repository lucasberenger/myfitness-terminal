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

## CLI interativa

Com a API ativa em outro terminal:

```sh
uv run fitness-chat
```

Digite mensagens normalmente; a resposta aparece com quebras de linha reais.
O cliente usa HTTP e a biblioteca padrão do Python, sem novas dependências.
Ele não acessa o PostgreSQL nem precisa receber a chave Groq.

```text
Você > Quais alimentos com arroz estão cadastrados?
Você > Registre 150 g desse arroz no almoço de hoje.
Você > Na verdade, foram 200 g.
Você > Qual o total de hoje?
```

Comandos:

- `/new`: iniciar outra conversa, sem apagar refeições ou histórico do servidor.
- `/conversation`: mostrar o ID atual.
- `/help`: mostrar ajuda.
- `/exit` ou `/quit`: sair; Ctrl+D e Ctrl+C também encerram a sessão.

O identificador é salvo em `.fitness-chat.json` no diretório atual, separado
por URL da API. Esse arquivo está ignorado pelo Git e não contém o texto das
mensagens. Para retomar automaticamente, execute no mesmo diretório.
Evite executar dois clientes usando o mesmo arquivo de sessão ao mesmo tempo.

Para continuar uma conversa criada no Swagger:

```sh
uv run fitness-chat --conversation 5d32ef20-db75-4799-82c3-c834d232244d
```

Outras opções:

```sh
uv run fitness-chat --new
uv run fitness-chat --api-url http://127.0.0.1:8000 --timeout 60
uv run fitness-chat --state-file /tmp/minha-sessao-fitness.json
uv run fitness-chat --help
```

O timeout padrão do cliente é 45 segundos; ajuste-o para ficar acima do prazo
configurado no agente. Em falhas de rede, não há reenvio automático. O servidor
pode ter concluído a operação mesmo que a resposta não tenha chegado: consulte o
resumo antes de repetir uma gravação. Uma conversa inexistente retorna erro e
sugere `/new`, sem criar outra silenciosamente.

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
3. Ampliar a experiência da CLI e os cenários de avaliação.
4. Adicionar idempotência, metas e avaliações do agente.

`GROQ_API_KEY` e `GROQ_MODEL` ficam no `.env`.
O comando `fitness-chat` inicia o cliente interativo de terminal.

## Proteção da resposta final

Respostas vazias, acima de 6000 caracteres, com uma mesma linha não vazia
repetida oito vezes ou mais, ou finalizadas por motivo diferente de `stop`
são rejeitadas. Há uma tentativa de gerar novamente apenas o texto final, com
ferramentas desabilitadas, respeitando o prazo e o limite de rodadas existentes.
Se ela falhar, a transação é desfeita. Essa heurística não detecta toda resposta
incorreta ou incoerente. Respostas antigas com esses sinais são omitidas do
contexto enviado ao modelo, preservando os resultados das ferramentas.
