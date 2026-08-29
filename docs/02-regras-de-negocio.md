# Regras de negócio

> Fonte única das regras. No código elas se **referenciam por número**
> (`# RN-012`), nunca se transcrevem — texto duplicado diverge.

Vocabulário: [`01-dominio.md`](01-dominio.md). Ameaças e testes que provam as
mitigações: [`05-threat-model.md`](05-threat-model.md) (a escrever).

**Numeração.** Blocos de dez por área, com folga deliberada para crescer sem
renumerar. Regra revogada permanece no documento com status `revogada`, data e
motivo — número nunca é reaproveitado.

**Status.** Toda regra abaixo está `ativa` salvo indicação em contrário.
"Verificação" é onde a regra é imposta e o que prova que ela vale; enquanto o
código não existe, é o compromisso de onde ela vai morar.

---

## 1. Integridade do caso (RN-001 … RN-009)

**RN-001** — Todo caso tem exatamente um culpado.
*Verificação:* invariante do gerador, checada na validação do caso.

**RN-002** — Um caso só é publicável se um *solver* automático provar que existe
caminho de dedução alcançável a partir dos fatos de escopo público. Caso que não
passa é descartado e regerado.
*Verificação:* portão de publicação no gerador; caso reprovado nunca chega a
`Briefing`.

**RN-003** — Todo suspeito não-culpado tem um segredo próprio, irrelevante para
o crime, que o faz mentir. Sem isso o jogo vira "quem está nervoso".
*Verificação:* invariante do gerador; teste unitário sobre o elenco gerado.

**RN-004** — A linha do tempo não pode conter sobreposição física impossível
(mesmo personagem em dois cômodos no mesmo intervalo).
*Verificação:* validador determinístico de linha do tempo, com teste de
propriedade sobre casos gerados.

**RN-006** — A memória de um NPC só aceita fatos vindos do dossiê. Texto do
jogador nunca vira fato, nem quando o jogador afirma algo verdadeiro.
*Verificação:* a escrita na memória só aceita `id` de fato existente no dossiê;
teste unitário planta um "fato" via input e confirma que ele não persiste.
Mitiga T-06 (envenenamento de memória).

---

## 2. Isolamento de conhecimento (RN-010 … RN-019)

**RN-010** — Um NPC só recebe no contexto fatos cujo escopo o inclui.
*Verificação:* dossiê montado por consulta de escopo (não por filtro em prompt);
golden set `escopo.jsonl` — 40 perguntas sobre fatos que o NPC não deveria
conhecer.

**RN-011** — A entidade `Solucao` nunca entra no contexto de um NPC suspeito. O
culpado sabe apenas da própria culpa; não sabe o que os outros sabem.
*Verificação:* fronteira de tipo — nenhuma função de montagem de contexto recebe
`Solucao`; canary da solução no golden set de vazamento.

**RN-012** — Todo fato secreto carrega um canary token. Presença de canary na
saída é falha crítica: resposta descartada, incidente registrado.
*Verificação:* filtro de saída obrigatório; gate de CI em **0%** de vazamento —
bloqueia merge.

**RN-013** — Cada NPC tem sessão de memória isolada. Não existe barramento de
contexto compartilhado entre NPCs, exceto por eventos de fofoca explícitos
(fase 3).
*Verificação:* memória particionada por `(partida, personagem)`; teste de
integração pergunta a B o que só A ouviu.

---

## 3. Comportamento do NPC (RN-020 … RN-029)

**RN-020** — Um NPC mente apenas sobre fatos que o incriminam ou expõem seu
segredo. Sobre fatos públicos verificáveis ele diz a verdade.
*Verificação:* `mentiu` na saída estruturada cruzado com o escopo do
`fato_referenciado`; mentira fora dessas condições é regressão de prompt.

**RN-021** — Um NPC não pode contradizer declaração própria anterior, salvo
quando confrontado com prova que a invalide. Nesse caso a mudança é um evento de
jogo (`quebra_de_alibi`), não um bug.
*Verificação:* detector determinístico de contradição sobre as declarações
persistidas; gate de evals ≤ 2% de contradições não intencionais.

**RN-022** — Cada resposta retorna estruturada:
`{ fala, postura, mentiu: bool, fato_referenciado: id|null, pista_vazada: id|null }`.
A pontuação usa os campos, não a fala.
*Verificação:* schema Pydantic versionado; resposta que não valida é rejeitada e
o turno não é debitado.

**RN-023** — Postura evolui por máquina de estados determinística
([`01-dominio.md` §6](01-dominio.md)). O LLM *sugere* transição; o backend valida
contra as regras e mantém a postura atual se a sugestão for inválida.
*Verificação:* teste unitário da máquina de transição, independente do modelo.

---

## 4. Progressão e veredito (RN-030 … RN-039)

**RN-030** — Orçamento padrão: 30 turnos. Confronto custa 2 turnos.
*Verificação:* débito no fechamento do turno; turno com resposta rejeitada por
schema não debita (ver RN-022), turno bloqueado por injeção debita (RN-041).

**RN-031** — Uma acusação por partida, irreversível.
*Verificação:* transição de estado da partida; segunda acusação é erro de
domínio, não `409` genérico.

**RN-032** — O veredito é calculado por código determinístico comparando a
acusação com `Solucao`. O LLM apenas narra o desfecho já decidido.
*Verificação:* o narrador recebe o veredito pronto como entrada; teste com LLM
mockado prova que o resultado não depende do modelo.

**RN-033** — Pontuação = acerto do culpado (peso 60) + provas corretas
apresentadas (30) + turnos economizados (10).
*Verificação:* função pura, testada por tabela de casos.

---

## 5. Antiabuso (RN-040 … RN-049)

**RN-040** — Entrada do jogador passa por classificador de intenção antes de
chegar ao NPC. Categorias: `pergunta`, `confronto`, `meta`, `injecao`.
*Verificação:* golden set `injecao.jsonl` (60 tentativas); gate ≥ 95% de
resistência.

**RN-041** — Entrada classificada como `injecao` não chega ao LLM do NPC.
Resposta canônica em personagem, turno debitado.
*Verificação:* teste de integração confirma que o provedor não é chamado; o
evento é registrado como `tentativa_injecao`.

**RN-042** — Saída passa por filtro de canary e por checagem de escopo antes de
chegar ao cliente.
*Verificação:* filtro aplicado também no caminho de streaming — buffer mínimo
antes de emitir, para que canary partido entre chunks não escape.

---

## Regras revogadas

Nenhuma até aqui.
