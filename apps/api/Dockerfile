# Imagem de desenvolvimento. A de produção (multi-stage, distroless) chega na
# fase 7, junto com o pipeline de build — ver docs/00-plano-de-projeto.md §8.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir -e .

EXPOSE 8000
CMD ["uvicorn", "mansao.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
