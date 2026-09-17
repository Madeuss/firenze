# Runbook

O que existe na Magalu Cloud, como chegar até lá, e o que fazer quando não dá.

O `CLAUDE.md` aponta para este arquivo desde o começo do projeto e ele não
existia — a instrução estava certa e o documento não. Nasceu no dia em que a
infraestrutura deixou de ser plano.

## O que está de pé

| Recurso | Nome | Onde | Detalhe |
|---|---|---|---|
| Banco gerenciado | `firenze-db` | `172.30.0.55:5432`, privado | PostgreSQL 16.14, BV1-4-10 (1 vCPU, 4 GB), 10 GiB criptografado |
| VM bastião | `firenze-bastion` | `201.23.2.157` público, `172.30.0.11` privado | Ubuntu 24.04 LTS, BV1-2-10 (1 vCPU, 2 GB, 10 GB) |
| Rede | `vpc_default` | `br-ne1-a` | Os dois na mesma sub-rede `172.30.0.0/25` |

Backup do banco retido por 7 dias. Extensão `vector` **0.8.5** instalada — mais
nova que a 0.8.2 que o plano registrava.

## A restrição que organiza tudo

**O DBaaS só tem IP privado.** Não existe flag de acesso público no `mgc dbaas
instances create`, e não é descuido de configuração: é como o produto é. Da sua
máquina não há rota, e nunca vai haver.

Por isso existe o bastião. Tudo que fala com o banco de fora da VPC —
`alembic`, `psql`, um script de carga — passa por um túnel SSH por ele.

## Abrir o túnel

```bash
ssh -N -L 55432:172.30.0.55:5432 ubuntu@201.23.2.157
```

Deixe rodando numa aba. A partir daí, `localhost:55432` é o banco gerenciado.

A chave é a `desktop-windows-mateus`, a mesma que já estava na conta Magalu;
localmente ela é a `~/.ssh/id_rsa`. Se o SSH pedir senha, a chave errada está
sendo oferecida — `ssh -i ~/.ssh/id_rsa` resolve.

## Rodar migration no banco gerenciado

Com o túnel aberto:

```bash
cd apps/api
FIRENZE_DATABASE_URL="postgresql+psycopg://firenze:$MGC_DB_PASSWORD@localhost:55432/firenze" \
  uv run alembic upgrade head
```

A senha vive no `.env` da raiz como `MGC_DB_PASSWORD`, e **só ali**. Não está em
nenhum commit, nem no histórico do shell: o comando que criou a instância foi
montado dentro de um script justamente para o valor não passar pela linha de
comando.

## Quando não conecta

**`Connection refused` no `localhost:55432`.** O túnel caiu. SSH não avisa; ele
só some. Reabra.

**O `ssh` entra mas o túnel não sobe.** Suba com `-o ExitOnForwardFailure=yes`,
que transforma "a porta local já está em uso" em erro em vez de silêncio.

**Do bastião não alcança o banco.** Conferir a rota é uma linha, e não precisa
de `psql` instalado lá:

```bash
ssh ubuntu@201.23.2.157 "timeout 8 bash -c '</dev/tcp/172.30.0.55/5432' && echo aberta"
```

Se fechar, o caminho é o security group da interface do bastião
(`10518adc-4b7b-46e4-871d-b6f61a70e3ab`) contra o do banco. Hoje o padrão da
`vpc_default` já libera tráfego interno e nenhuma regra precisou ser criada.

**A instância sumiu do `mgc dbaas instances list`.** Ela pode estar parada:
`mgc dbaas instances start <id>`. Parar é uma operação de custo, não de
emergência — instância parada não cobra computação, mas continua cobrando disco.

## Ids, para não caçar de novo

```
banco    5189cd9b-2a21-4a22-aaae-c406100ee360
vm       4c39d686-dde8-4f86-8a00-1ab28c0a09a0
vpc      d76f1474-30de-4e7d-954d-824a8b59b54f
engine   89bd25d5-e29e-4615-a64b-0a006bbc4997   (postgresql 16)
máquina  9f99f51e-4405-4c29-867f-46a642ce5f42   (BV1-4-10)
```

## O que ainda não existe

A API **não roda** na nuvem. O que está lá é banco e bastião; o jogo continua
subindo local pelo `make dev` e apontando para o Postgres de contêiner. Colocar
a API na VM é o passo seguinte, e ele traz decisões que este runbook ainda não
tem: como a chave do modelo chega na VM, o que serve o front, e quem tem
permissão de começar uma partida — que é a [T-11](05-threat-model.md), aberta
desde que o threat model foi escrito.
