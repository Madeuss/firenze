# Duas imagens em um arquivo, e a diferença entre elas é a diferença entre as
# duas situações — não duas cópias que vão divergir no primeiro mês.
#
# O contexto de build é a **raiz do repositório**, não `apps/api`. Os prompts
# vivem em `prompts/` por convenção (CLAUDE.md) e são carregados em tempo de
# execução, então precisam entrar na imagem — e não dá para copiar de fora do
# contexto. Ver `infra/compose/docker-compose.yml`.
FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY apps/api/pyproject.toml ./
COPY apps/api/src ./src
RUN pip install --no-cache-dir -e .

COPY apps/api/alembic.ini ./
COPY apps/api/migrations ./migrations
COPY prompts ./prompts

# Dentro do container não existe raiz de repositório para contar diretórios
# até ela. O caminho é explícito, e `prompts_dir()` prefere esta variável.
ENV FIRENZE_PROMPTS_DIR=/app/prompts

COPY apps/api/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["docker-entrypoint.sh"]


# Desenvolvimento: recarrega ao salvar, e o compose monta `src/` e `prompts/`
# por cima para que salvar baste.
FROM base AS dev
CMD ["uvicorn", "firenze.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


# Produção.
FROM base AS prod

# Usuário sem privilégio: um processo que só precisa ler o próprio código não
# tem por que poder reescrevê-lo.
RUN useradd --system --uid 10001 firenze && chown -R firenze:firenze /app
USER firenze

# Um worker, deliberadamente. O limitador de T-12 conta em memória, e dois
# processos contariam metade cada um — na prática, o dobro do limite. Quando
# houver motivo para mais de um, o contador vai para o Redis antes.
#
# Sem `--reload`: além do custo, ele observa o disco e reinicia sozinho, o que
# num servidor transforma qualquer escrita acidental em queda de serviço.
CMD ["uvicorn", "firenze.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
