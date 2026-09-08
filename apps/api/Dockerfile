# Imagem de desenvolvimento. A de produção (multi-stage, distroless) chega na
# fase 7, junto com o pipeline de build — ver docs/00-plano-de-projeto.md §8.
#
# O contexto de build é a **raiz do repositório**, não `apps/api`. Os prompts
# vivem em `prompts/` por convenção (CLAUDE.md) e são carregados em tempo de
# execução, então precisam entrar na imagem — e não dá para copiar de fora do
# contexto. Ver `infra/compose/docker-compose.yml`.
FROM python:3.13-slim

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
CMD ["uvicorn", "firenze.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
