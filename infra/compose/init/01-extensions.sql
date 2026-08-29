-- Roda uma vez, na criação do volume. Para reexecutar: make down && docker volume rm mansao_pgdata
--
-- pgaudit fica de fora aqui de propósito: exige shared_preload_libraries e não
-- vem na imagem pgvector. É extensão do DBaaS da Magalu (ADR-0002), habilitada
-- via terraform em infra/terraform.
--
-- Drift de versão: a imagem traz pgvector 0.8.6, o DBaaS da Magalu está em
-- 0.8.2. Antes de usar recurso novo de índice, confirme que existe lá.

CREATE EXTENSION IF NOT EXISTS vector;     -- memória dos NPCs (ADR-0002)
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- busca híbrida: nomes próprios e horários
CREATE EXTENSION IF NOT EXISTS unaccent;   -- português

-- Falha alto e cedo se a imagem não tiver o que prometemos.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        RAISE EXCEPTION 'pgvector ausente — imagem errada no compose';
    END IF;
    RAISE NOTICE 'extensões ok: vector %, pg_trgm, unaccent',
        (SELECT extversion FROM pg_extension WHERE extname = 'vector');
END
$$;
