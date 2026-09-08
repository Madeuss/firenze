#!/bin/sh
# Migra antes de servir, para que `make dev` num clone novo dê uma pilha
# jogável em vez de uma que responde /health e falha no primeiro turno.
#
# Só no compose de desenvolvimento. Em produção migration é passo do deploy,
# com janela e rollback — não algo que cada réplica decide fazer ao subir
# (docs/07-runbook.md, quando existir).
set -e

if [ "${FIRENZE_MIGRATE_ON_BOOT:-1}" = "1" ]; then
  echo "aplicando migrations…"
  alembic upgrade head
fi

exec "$@"
