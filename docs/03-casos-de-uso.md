# Casos de uso

> O que o jogador vê, onde ele clica e onde ele digita. Este documento decide a
> fase 5; a API que ele consome já existe.

Vocabulário: [`01-dominio.md`](01-dominio.md). Regras citadas por número:
[`02-regras-de-negocio.md`](02-regras-de-negocio.md).

**Direção visual escolhida.** *The Case of the Golden Idol* na acusação (frase
com lacunas que o jogador monta), *Return of the Obra Dinn* no caderno (o que
falta descobrir aparece sem virar dica), *Monument Valley* na planta
(arquitetura isométrica chapada, sem textura e sem asset importado).

---

## 1. A regra que organiza a tela inteira

**Texto livre existe em exatamente dois lugares:** a pergunta a um suspeito, e a
acusação escrita com as próprias palavras. Todo o resto é clique.

Isso não é economia de trabalho. É o que faz a confirmação da acusação valer
alguma coisa: não existe caminho em que prosa vira ação sem passar por uma tela
de revisão (RN-031). O endpoint de acusação não aceita prosa — aceita campos —
e essa fronteira é do backend, não da boa vontade do front.

## 2. Uma tela, dois modos

O jogo alterna entre falar e pensar, e a interface nomeia isso. **Perguntar
custa turno; pensar é de graça.** Deixar isso explícito é metade do design: o
jogador precisa sentir que pode raciocinar sem estar sendo cobrado.

### Modo Interrogatório

```
┌─ Caso 42 · jardim de inverno · 21h30 ────── 27 turnos ── [Acusar] ─┐
│ ELENCO      │  Vitória Belmiro                    cooperativa      │
│ ● Vitória   │  ─────────────────────────────────────────────────   │
│ ○ Clarice   │  você — onde você estava às 22h?                     │
│ ○ Teodoro   │  Vitória — Na biblioteca, lendo. A noite toda.       │
│ ○ Godofredo │                                                      │
│ ○ Ilma      │  ┌────────────────────────────────────────────────┐  │
│ ○ Nazareno  │  │ pergunte alguma coisa…                    [→]  │  │
│             │  └────────────────────────────────────────────────┘  │
│             │  provas: [F-001 corpo] [F-014 castiçal]  ← arraste   │
└─────────────┴──────────────────────────────────────────────────────┘
```

- O elenco à esquerda mostra a **postura** de cada suspeito, que muda sozinha
  conforme a conversa (RN-023). Postura é o único estado do NPC que o jogador
  enxerga.
- **Acusar** e **?** ficam à direita no topo, sempre. Acusar no turno 1 é jogada
  legítima; e as regras não podem viver só na tela inicial, que some no primeiro
  clique.
- O caderno da API é a **única fonte** da conversa, e traz todo turno cobrado —
  inclusive os que não produziram fala. O front não guarda cópia do que
  aconteceu; se guardasse, teria duas versões da mesma verdade e elas
  divergiriam.
- O input embaixo é o único campo de texto do jogo.
- As provas ficam numa bandeja logo abaixo. Arrastar uma para o input arma um
  confronto e o botão muda para **"Confrontar — custa 2 turnos"**. O custo
  aparece antes do clique, nunca depois.

### Modo Dedução

```
┌─ Dedução ──────────────────────────── não gasta turno ─┐
│                                                        │
│      ╱▔▔▔╲  planta isométrica (Three.js)   21h 22h 23h │
│     ╱ ▫▫▫ ╲  clique num cômodo             Vitória ▪▪· │
│    ╱ ▫▫▫▫▫ ╲ arraste a linha do tempo      Clarice ·▪· │
│    ╲ ▫▫▫▫▫ ╱                               Teodoro ··▪ │
│     ╲ ▫▫▫ ╱                                            │
│      ╲▁▁▁╱   [21h00 ●──────── 23h30]                   │
└────────────────────────────────────────────────────────┘
```

**A planta começa vazia, e o jogador é quem preenche.** Ele clica numa célula da
grade (suspeito × horário), escolhe um cômodo, e o boneco aparece lá quando a
linha do tempo chega naquele intervalo. Duas anotações no mesmo cômodo no mesmo
horário acendem.

Isso é deliberado e é o coração do desenho: **se o servidor entregasse a planta
preenchida, ele resolveria o jogo.** A API expõe a planta vazia — quais cômodos
existem e quais horários a noite cobre — e nada sobre quem alegou o quê. Montar
o mapa *é* a dedução.

Planta responde *onde*; a grade ao lado responde *quando*. As duas juntas dentro
do mesmo espaço 3D viram confusão, então ficam lado a lado.

## 3. Mapa de cliques

| Ação | Onde | Custa | Endpoint |
|---|---|---|---|
| Começar partida | tela inicial, semente opcional | — | `POST /matches` |
| Trocar de suspeito | elenco à esquerda | grátis | — |
| Perguntar | input central, Enter | 1 turno | `POST /matches/{id}/turns` |
| Confrontar | arrastar prova → input | 2 turnos | `POST /matches/{id}/confrontations` |
| Alternar modo | aba no topo | grátis | — |
| Anotar na planta | célula da grade, em Dedução | grátis | local (ver §7) |
| Escrever acusação | botão Acusar → campo livre | grátis | `POST …/accusation/draft` |
| Confirmar acusação | tela de revisão da frase | **encerra** | `POST …/accusation` |
| Rever a partida | após o veredito | — | `GET /matches/{id}/review` |

O botão **Acusar** fica sempre visível, no topo. Acusar no turno 1 é uma jogada
legítima — e vale mais pontos de rapidez se der certo (RN-033).

## 4. Um gameplay de ponta a ponta

Semente 42, pt-BR. Os nomes e fatos abaixo são os que o gerador produz de
verdade para essa semente.

**Briefing.** *"O corpo de Rodolfo Andrade foi encontrado no jardim de inverno,
por volta das 21h30."* É o único fato público. Seis suspeitos, 30 turnos.

**Turno 1.** O jogador clica em Ilma Prado e digita *"onde você estava às 22h?"*.
Ela responde de forma evasiva — Ilma esconde dívidas de jogo e estava mesmo no
escritório às 22h, então mente sobre isso (RN-003, RN-020). A postura dela no
elenco vira **evasiva**, sem ninguém mandar.

**Turno 2 — grátis.** Modo Dedução. O jogador anota: Ilma → 22h00 → o cômodo que
ela alegou.

**Turnos 3-4.** Teodoro Mainz é o mais bem informado do elenco (11 fatos). Ele
deixa escapar uma pista: a resposta traz `clue_revealed`, e uma ficha nova
aparece na bandeja de provas. O jogador não pediu — o NPC entregou.

**Turno 5 — grátis.** Na planta, duas anotações colidem no escritório às 22h30.
A célula acende. Isso é trabalho do jogador, não do servidor.

**Turnos 6-7.** O jogador arrasta a ficha do Teodoro para o input com Ilma
selecionada: **"Confrontar — custa 2 turnos"**. Ela quebra. `alibi_broken` volta
verdadeiro e a postura vai para **quebrada** — um estado que o modelo não pode
sugerir e ao qual só a prova chega (RN-023).

**Turno 12 — uma resposta que não vem.** O filtro de saída descarta a resposta
(RN-042). A tela diz que não veio resposta e que o turno foi gasto. Não inventa
desculpa em personagem — ver §5.

**Por volta do turno 20.** O jogador encontra o fato do motivo: a herança que
seria redirecionada na manhã seguinte. **Só agora** o motivo fica nomeável. Antes
disso o jogo não oferece a lista, porque escolher entre quatro motivos não é
dedução, é sorteio de 20 pontos (RN-034).

**Acusação.** Botão Acusar. O jogador escreve *"foi a Vitória, por causa da
herança, e a prova é o castiçal"*. A tela do Golden Idol se monta:

> Você vai acusar **Vitória Belmiro**, por **herança que seria redirecionada na
> manhã seguinte**, apresentando **castiçal de bronze**.
>
> *Não consegui identificar: "o castiçal"* → escolha uma prova
>
> **Isto não pode ser desfeito.**

O que o parser não conseguiu encaixar volta ao jogador em vez de ser adivinhado
(RN-031). Ele corrige clicando, confirma, e o veredito vem: culpado (50), motivo
(20), provas proporcionais, rapidez. Mais o epílogo em prosa — que, se o modelo
estiver fora do ar, simplesmente não aparece, sem mudar um ponto da nota
(RN-032).

**Revisão.** A planta se preenche sozinha com o que foi de fato alegado. Os
turnos aparecem em ordem, inclusive os que não produziram nada, e o jogador vê
onde gastou à toa (RN-035).

## 5. Vocabulário de interface

Uma palavra por coisa. Se o domínio já tem nome, a tela usa o mesmo.

| Conceito | Na tela | Por quê |
|---|---|---|
| Orçamento | **turnos** | Não é relógio. "Tempo" prometeria pressão que o jogo não exerce — pensar é de graça — e colidiria com o relógio de ficção da noite (21h00–23h30). |
| Modos | **Interrogatório** / **Dedução** | Nomeia a diferença que importa: um custa, o outro não. |
| Fatos que o jogador tem | **provas** | `Evidence` no domínio. Fato só vira prova depois de descoberto. |
| Registro da partida | **caderno** | É do jogador, não do sistema. |
| Estado do NPC | **cooperativo / evasivo / hostil / quebrado** | Os quatro estados da máquina, sem sinônimo. |
| Fim | **Acusar** | Não "resolver", não "fechar o caso": o jogo é sobre apontar alguém, e pode estar errado. |

**Tom.** Segunda pessoa, presente, econômico. Sem exclamação, sem elogio
("Ótimo trabalho!"). O jogo é sombrio e a interface não comemora.

**Regra: turno rejeitado não ganha desculpa em personagem.** Quando o filtro
descarta uma resposta, a tentação é escrever *"ela hesita e não responde"*. Isso
seria mentir — uma falha de sistema apareceria como pista, e o jogador tiraria
conclusão dela. A tela diz o que houve: não veio resposta, o turno foi gasto. A
API já foi desenhada para isso, devolvendo `reason` grosseiro em vez de detalhe
(o detalhe pode conter o canary, ver [T-02](05-threat-model.md)).

### Idioma: escolhido uma vez, no começo

O idioma é **propriedade da partida** ([ADR-0005](adr/0005-locale-is-a-property-of-the-match.md)),
e o único momento em que se escolhe é a tela inicial, ao lado da semente. Depois
não muda, e a razão não é preguiça de implementar: o caderno guarda o que os
suspeitos já disseram, no idioma em que disseram. Trocar no meio deixaria uma
partida bilíngue, com metade das respostas numa língua e metade na outra.

A interface segue `match.locale` em vez de uma preferência do navegador. Botão
em inglês com mordomo respondendo em português seria pior que ter um idioma só.

**Perguntar num idioma e ser respondido noutro é permitido, e é assim de
propósito.** O suspeito responde no idioma da partida — a casa é dela, não da
pergunta. Nada valida o que o jogador digita: a classificação de intenção
(RN-040) olha o que a pergunta *quer*, não em que língua ela está.

Nomes próprios não se traduzem. Uma mansão brasileira mantém nomes brasileiros
em qualquer idioma; traduzi-los soaria a dublagem ruim. As **funções**, sim, são
conteúdo e vêm do catálogo da API — `mordomo` e `butler` são a mesma chave.

## 6. Paleta e tipografia

**Direção:** Monument Valley numa mansão à noite. Chapado, pouca saturação, uma
única cor quente que só aparece onde há ação.

| Papel | Cor |
|---|---|
| Fundo, a noite | índigo escuro, quase carvão |
| Papel do caderno | creme quente, nunca branco |
| Ação — botão, foco | **osso**, mais claro que o papel e com mais peso |
| Alerta — contradição, álibi quebrado | vermelhão apagado |
| Posturas | verde-azulado → âmbar → vermelhão → violeta acinzentado |

O acento é ausência de cor, e isso é a decisão: com a ação em osso, **o alerta
fica sendo a única cor viva da tela**. Contradição e álibi quebrado saltam sem
competir com botão nenhum. Botão claro corre o risco de ler como rótulo — quem
resolve isso é peso e sombra, não cor.

**Tipografia:** serifada para a fala dos suspeitos, que é o que se lê muito; sem
serifa para a interface; monoespaçada para id de fato (`F-014`).

- **Newsreader** (fala) + **Inter** (interface) + **JetBrains Mono** (ids)
- Alternativa mais sóbria: **Source Serif 4** + **Public Sans**

As duas combinações cobrem acentuação pt-BR sem cair para fonte substituta.

Nada disto é definitivo — cor e fonte são a parte mais barata de trocar, e a
estrutura acima não depende delas.

## 7. O que a API entrega para a planta

`MatchState.plan` traz a casa e a noite — `rooms` com id estável e nome no
idioma da partida, `hours` com índice e rótulo de relógio. É constante durante
a partida e **não contém pessoa nenhuma**: reconstruir a noite a partir do que
foi alegado é a dedução, e servidor que entrega planta preenchida resolve o
jogo.

Na revisão, `ReviewedTurn` carrega `claimed_room` e `claimed_interval`, e a
planta se preenche sozinha com o que cada um alegou (RN-035). A resposta de um
turno, durante a partida, continua sem esses campos.

**Anotação do jogador fica no navegador**, por enquanto. Persistir exige decidir
de quem é a partida, e isso esbarra em
[T-11](05-threat-model.md) — não há autenticação. A ordem correta é resolver a
posse da partida antes de guardar qualquer coisa que o jogador escreveu.
