# Runbook

O que existe na Magalu Cloud, como chegar até lá, e o que fazer quando não dá.

O `CLAUDE.md` aponta para este arquivo desde o começo do projeto e ele não
existia — a instrução estava certa e o documento não. Nasceu no dia em que a
infraestrutura deixou de ser plano.

## O que está de pé

Tudo em **`br-se1`** (sudeste). Nasceu por engano no nordeste e foi refeito:
ver "Trocar de região" no fim.

| Recurso | Nome | Onde | Detalhe |
|---|---|---|---|
| Banco gerenciado | `firenze-db` | `172.40.0.12:5432` | PostgreSQL 16, BV1-4-10 (1 vCPU, 4 GB), 10 GiB criptografado |
| VM bastião | `firenze-bastion` | `201.23.64.197` público, `172.40.0.27` privado | Ubuntu 24.04 LTS, BV1-2-10 (1 vCPU, 2 GB, 10 GB) |
| Rede | `vpc_default` | `br-se1-a` | Os dois na mesma VPC `0d038ade…` |

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
ssh -N -L 55432:172.40.0.12:5432 ubuntu@201.23.64.197
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
que transforma "a porta local já está em uso" em erro em vez de silêncio. Foi
exatamente o que aconteceu ao refazer a região: um túnel antigo ainda segurava
a 55432, e sem a flag o SSH teria ficado de pé sem encaminhar nada — conexão
recusada do outro lado, sem pista do motivo. A mensagem é
`Could not request local forwarding`.

**Do bastião não alcança o banco.** Conferir a rota é uma linha, e não precisa
de `psql` instalado lá:

```bash
ssh ubuntu@201.23.64.197 "timeout 8 bash -c '</dev/tcp/172.40.0.12/5432' && echo aberta"
```

Se fechar, o caminho é o security group da interface do bastião
(`f5fc0ae5-c45f-45a8-bb2a-3d7263c6160c`) contra o do banco. Hoje o padrão da
`vpc_default` já libera tráfego interno e nenhuma regra precisou ser criada.

**A instância sumiu do `mgc dbaas instances list`.** Ela pode estar parada:
`mgc dbaas instances start <id>`. Parar é uma operação de custo, não de
emergência — instância parada não cobra computação, mas continua cobrando disco.

## Ids, para não caçar de novo

```
banco    f900ea96-5feb-4f32-b12a-208bdfce2492
vm       739840dd-82c6-4ccb-9b14-e3d251bf7057
vpc      0d038ade-f8d0-4704-8edf-3c263c3c510b
engine   89bd25d5-e29e-4615-a64b-0a006bbc4997   (postgresql 16)
tipo db  9f99f51e-4405-4c29-867f-46a642ce5f42   (BV1-4-10)
imagem   e56e9ec4-b149-40d4-8774-3d58ba075c21   (ubuntu 24.04, **só em se1**)
máquina  fc8641f6-f3a4-407c-8612-5576dd9ffdc6   (BV1-2-10, **só em se1**)
```

## Trocar de região

A CLI obedece a `mgc config set region <br-se1|br-ne1>`, e recurso nenhum
atravessa: para apagar algo criado na outra região é preciso voltar a
configuração para ela primeiro, senão o `list` devolve vazio e parece que já
não existe.

E os ids **não são os mesmos nas duas**. Os do DBaaS até coincidem — engine e
tipo de instância têm o mesmo uuid em `ne1` e `se1` —, mas os da VM não:
imagem e tipo de máquina mudam, e usar o uuid da outra região falha na criação.
Consulte sempre, nunca copie do runbook antigo.

## Subir a API

A pilha de produção é `infra/compose/docker-compose.prod.yml`: a API atrás de um
Caddy que emite o certificado sozinho. Sem Postgres (é gerenciado) e sem Redis
(não tem uso ainda).

O nome é `201.23.64.197.sslip.io` — `sslip.io` resolve qualquer nome que
contenha um IP para aquele IP, então o Let's Encrypt emite certificado de
verdade sem domínio comprado. Trocar por um domínio próprio é mudar
`FIRENZE_DOMAIN` e recarregar.

```bash
git archive --format=tar HEAD -o /tmp/firenze.tar
scp /tmp/firenze.tar ubuntu@201.23.64.197:/tmp/
ssh ubuntu@201.23.64.197 'cd /opt/firenze && tar xf /tmp/firenze.tar'
ssh ubuntu@201.23.64.197 'cd /opt/firenze/infra/compose &&   sudo docker compose -f docker-compose.prod.yml build &&   sudo docker compose -f docker-compose.prod.yml up -d'
```

Tarball do commit, e não `git clone`: a VM não precisa de credencial de git, e o
que sobe é exatamente o que está commitado.

**Migration é passo do deploy, nunca do boot.** A VM está dentro da VPC, então
fala com o banco gerenciado sem túnel:

```bash
sudo docker compose -f docker-compose.prod.yml run --rm --entrypoint alembic api upgrade head
```

**Os segredos** vivem em `/opt/firenze/infra/compose/.env`, modo 600, escritos
por `stdin` do SSH — nunca por linha de comando, que ficaria no histórico. A
chave de convite (`FIRENZE_ACCESS_KEY`) é a mesma no `.env` da raiz do repo, que
é de onde o front a lê.

E a trava: **um processo com `FIRENZE_ENVIRONMENT=prod` sem chave se recusa a
subir** (T-11). Testado contra a imagem, não só em teste unitário.

## O bloqueio que impede o jogo de funcionar lá

A VM **não alcança o AI Hub**. SYN descartado na 443 para
`api.inferencia.llm.mglu.io`, por IPv4 e IPv6, enquanto a saída para o resto da
internet funciona. Da minha máquina o mesmo endereço responde em 0,09s.

Então `/health` responde, partida é criada, o caderno é protegido — e nenhum
suspeito fala. Precisa de chamado para a Magalu. O diagnóstico completo está em
[08-achados.md](08-achados.md).

## O que ainda não existe

O front **não roda** na nuvem. Ele continua subindo local pelo `yarn dev` e
apontando para a API por `FIRENZE_API_URL`. Das três decisões que este runbook
não tinha, duas foram tomadas — a chave do modelo chega por `.env` escrito via
`stdin`, e quem pode começar partida responde a [T-11](05-threat-model.md), hoje
fechada. Falta o que serve o front: Vercel ou esta mesma VM.
