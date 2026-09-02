# Achados

> Log de descobertas, não de tarefas. Entra aqui o que surpreendeu, o que
> quebrou de um jeito que ensinou algo, e o que só se aprende fazendo.
> O roadmap está no [plano](00-plano-de-projeto.md); as decisões, em [`adr/`](adr/).

**Por que existe:** os detalhes bons evaporam. Daqui a três meses ninguém lembra
por que o fato-prova apontava para a pessoa errada, e é justamente esse tipo de
coisa que sustenta um artigo honesto — ou impede de reaprender o mesmo tropeço.

**Formato:** data, o que aconteceu, por que importa, link. Uma entrada por
descoberta. Se não surpreendeu ninguém, não é achado — é changelog.

---

## Domínio e geração

### 2026-08-29 — O validador se pagou no primeiro dia

Duas invariantes quebradas pelo próprio gerador, ambas passariam em revisão de
código, ambas pegas por checagem automática ([#11](https://github.com/Madeuss/firenze/pull/11)):

1. Dois inocentes podiam sortear o mesmo par (cômodo, intervalo) para o segredo.
   Esvaziar o cômodo para um deles arrastava o outro para longe do próprio
   segredo, e o fato passava a contradizer a linha do tempo.
2. O fato-prova marcava **quem achou** o objeto como a pessoa que ele localizava
   — colocando um inocente na cena do crime, na hora do crime.

**Por que importa:** é o argumento inteiro para validar o artefato pronto em vez
de confiar na intenção de quem gerou. Nenhum dos dois é erro de digitação; são
erros de modelagem, e modelagem errada lê como código certo.

### 2026-08-29 — Metade dos mistérios sorteados é insolúvel, e eles parecem bons

Não dá para gerar caso e confiar. O solver reprova, o caso é descartado e outro
nasce de semente derivada (RN-002). Sem esse portão, o jogador descobre o
problema depois de uma hora perdida.

**Por que importa:** é a diferença entre "gerei conteúdo com IA" e "gerei
conteúdo verificável". O verificador é mais interessante que o gerador.

### 2026-08-31 — O culpado não sabia que era culpado

O `Case` não carrega a solução, e a presença do culpado na cena nunca virou fato
— ninguém o viu, então não houve testemunha para gerar o fato. Resultado: o
dossiê dele não tinha nada de incriminador, e ele se comportaria exatamente como
um inocente sem álibi ([#20](https://github.com/Madeuss/firenze/pull/20)).

A RN-011 já previa: *"o culpado sabe apenas da própria culpa"*. A saída foi o
`Dossier` virar a fronteira — ele é o único lugar que lê a solução, e o que
atravessa é **um bit sobre si mesmo**, nada mais.

**Por que importa:** a regra estava certa e o código não a exercia. Só apareceu
quando o NPC precisou de fato responder — invariante que nunca foi exercitada é
invariante que ninguém verificou.

### 2026-08-31 — Falso deve omitir opcional, não inventar

O `FakeModel` preenchia `fact_referenced` com um id sintético, e o guard de
escopo rejeitava a resposta — corretamente, porque o id não existia no dossiê.
Campo opcional é campo que o modelo pode deixar de fora; inventar valor ali é
justamente o que a validação existe para pegar.

### 2026-08-31 — Semente sozinha não identifica um caso

`seed` só identifica junto com versão do gerador **e cenário**. Enquanto existe
um cenário só, nada é ambíguo — que é exatamente por que o campo custou cinco
minutos agora e seria migração depois ([#17](https://github.com/Madeuss/firenze/pull/17)).

**Por que importa:** reprodutibilidade é a base do eval. Um eixo esquecido na
identidade do caso faz baseline comparar coisas diferentes e reportar como
regressão do modelo.

---

## Modelos e IA

### 2026-08-29 — Quem escreve sabendo o culpado entrega o culpado

O verniz recebe `Case`, nunca `CaseWithSolution` — mesma disciplina do solver,
motivo diferente. Ninguém escreveria de propósito, mas o culpado ganharia a
descrição mais afiada ([#15](https://github.com/Madeuss/firenze/pull/15)).

O teste que vale é o forte: **cada suspeito aparece exatamente uma vez no
prompt**, na lista de elenco. Modelo que não consegue distingui-los não consegue
escrever um deles como mais culpado.

### 2026-08-29 — Canary na saída do verniz acusa a gente, não o modelo

O verniz só recebe fatos públicos. Como ele nunca vê um fato restrito, não pode
vazar um — então canary ali significa que a montagem de contexto quebrou
**antes** do modelo.

**Por que importa:** inverte o sentido da checagem. O mesmo filtro, no mesmo
lugar, testa coisas diferentes dependendo do que entrou no contexto.

### 2026-08-31 — Escrever a desvantagem numa ADR não é o mesmo que agir sobre ela

A ADR-0007 listou, em consequências negativas, *"dois adaptadores, um dos quais
nada em produção vai usar"* — e o adaptador ficou lá mesmo assim, até o usuário
perguntar por que ele existia ([#18](https://github.com/Madeuss/firenze/pull/18)).

**Por que importa:** documentar um custo dá a sensação de tê-lo endereçado. O
registro serve para decidir, não para absolver.

### 2026-08-31 — Um falso que satisfaz schema não satisfaz domínio

O `FakeModel` preenche qualquer schema, e a validação do verniz o rejeita —
porque o elenco que ele inventa não pertence a mistério nenhum. Correto, e é a
fronteira entre *"esse pipeline roda offline"* e *"isso dá para mostrar a um
jogador"*.

### 2026-08-31 — Quase todo um turno funciona sem modelo

Montar dossiê, validar schema, validar transição de postura, filtrar canary e
escopo, debitar turno: nada disso precisa de API. Só a fala soar em personagem
precisa.

**Por que importa:** derruba a premissa de que trabalho com LLM depende de chave
para começar. Depende para *terminar*.

### 2026-08-31 — Cobrança por token e por hora não se comparam direto

GPU cobra por hora ligada, usando ou não; API cobra por token. Com uso
intermitente de desenvolvimento, a economia inverte: o prompt do verniz mede
~400 tokens de entrada e ~400 de saída, ordem de US$ 0,0025 por caso em modelo
barato — contra uma VM que consome créditos dormindo.

---

## Idioma

### 2026-08-29 — Gramática portuguesa vazou para dentro do modelo de domínio

Um mapa `PREPOSICAO = {"adega": "na", "porão": "no"}` dentro do gerador. Inglês
não contrai preposição; alemão pediria três artigos
([#12](https://github.com/Madeuss/firenze/pull/12)).

**Por que importa:** frase pronta guardada como dado é uma decisão de idioma
tomada em silêncio. O sintoma aparece como conveniência.

### 2026-08-29 — Estrutura em vez de prosa se pagou duas vezes

Solver, validador e pontuação já raciocinavam sobre campos estruturados. Como
nada no caminho da dedução lê texto, tudo virou independente de idioma **sem uma
linha a mais**.

**Por que importa:** a decisão foi tomada por reprodutibilidade de eval e rendeu
i18n de graça. Decisão boa costuma pagar num eixo que não era o motivo dela.

### 2026-08-29 — Resistência a injeção varia por idioma

Jailbreak que falha em português passa em inglês, e vice-versa — modelos são
treinados de forma desigual entre línguas ([ADR-0005](adr/0005-locale-is-a-property-of-the-match.md)).

**Por que importa:** golden set adversarial precisa de casos **por idioma**, não
de tradução automática do conjunto português. Cada locale multiplica o custo de
eval, e português com pesos abertos é provavelmente a combinação mais difícil
que este projeto poderia escolher ([ADR-0008](adr/0008-magalu-prosa-as-the-model-provider.md)).

---

## Processo, CI e GitHub

### 2026-08-29 — Check obrigatório com filtro `paths:` trava o merge para sempre

Se o job não roda, ele nunca reporta, e o PR fica *pending* eternamente. Por isso
nenhum job obrigatório tem filtro de caminho.

### 2026-08-29 — `working-directory` global quebra job que não faz checkout

O `pr-title` não clona nada e falhava tentando entrar em `apps/api`. Default
global parece economia e é armadilha.

### 2026-08-29 — Ruleset não vale em repositório privado no plano Free

O ruleset estava configurado e **inerte**. Um merge commit passou apesar de
"require linear history" estar marcado na tela. A proteção só passou a valer com
o repositório público.

**Por que importa:** configurar não é o mesmo que estar protegido. Vale testar a
regra tentando violá-la.

### 2026-08-29 — Renomear branch pela API fecha o PR aberto

O endpoint de rename reaponta PR cujo *base* é a branch, mas **fecha** o PR cujo
*head* foi renomeado. Dois PRs morreram assim e precisaram ser recriados.

### 2026-08-29 — `Closes E1 (#5)` não fecha nada

O GitHub só reconhece a palavra-chave colada na referência: `Closes #5`. Com
qualquer coisa no meio, nenhum link é criado e a issue fica aberta. E para PR já
mergeado a janela fechou — não dá para corrigir depois.

### 2026-08-31 — A caixa de merge congela a mensagem quando a página abre

Editar o corpo do PR depois disso não chega ao commit. O `Closes #5` estava no
PR e não estava no merge — a issue não fechou.

### 2026-08-29 — PR empilhado diverge quando o de baixo entra squashed

O de cima carrega os commits originais, a main carrega a versão achatada, e todo
arquivo em comum conflita falsamente. Saída: rebase logo após o merge, ou merge
`-s ours` quando a árvore de cima já contém tudo que a main tem.

---

## Infra

### 2026-08-29 — `wsl.exe` do System32 é só um lançador

Habilitar os recursos por DISM não bastou: faltava `C:\Program Files\WSL`, e o
erro que o Docker mostrava era do lançador não achando o destino.
`winget install Microsoft.WSL` resolveu.

### 2026-08-29 — pgvector local e gerenciado divergem de versão

Imagem em 0.8.6, DBaaS da Magalu em 0.8.2. Recurso novo de índice precisa ser
conferido contra produção antes de ser usado
([ADR-0002](adr/0002-postgres-pgvector-instead-of-a-vector-database.md)).

### 2026-08-31 — Nenhum tipo de máquina com GPU na conta

50 tipos disponíveis, `gpu: 0` em todos, todos em `br-ne1`. O experimento com
modelo local da fase 8 não é só "depois" — precisa de pedido de quota antes.

---

## Ideias que nasceram do caminho

- **Detetive automático como eval.** Um agente que joga a partida só com o que o
  jogador vê prova que o caso é solucionável *na prática*; o solver prova que ele
  é dedutível *estruturalmente*. São garantias diferentes, e a segunda é mais
  convincente. Seria o primeiro lugar onde MCP faria trabalho de verdade neste
  projeto.
- **Comparar modelos abertos servidos pela Prosa contra a suíte adversarial, em
  português.** Ninguém publicou esse número.
