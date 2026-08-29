# ADR-0004: Estrutura do caso gerada por código, verniz gerado por LLM

## Status

Aceita — 2026-08-29

## Contexto

Um caso tem duas camadas que parecem uma só:

- **Estrutura** — quem é o culpado, quem estava em qual cômodo em qual
  intervalo, qual fato tem qual escopo, qual a cadeia que leva à dedução.
- **Verniz** — nomes, personalidades, descrição da cena, o texto que o jogador
  lê.

A estrutura é o que o solver precisa provar dedutível (RN-002), o que o
validador precisa checar (RN-001, RN-003, RN-004) e o que os evals precisam
reproduzir. O verniz é o que faz o jogo ter graça.

Três restrições pesam na escolha de quem gera a estrutura:

- **Reprodutibilidade.** A convenção do projeto é rodar todo eval cinco vezes
  porque temperatura > 0 torna uma execução inconclusiva. Se o próprio caso
  variar entre execuções, não sobra nada fixo para medir: uma regressão de
  prompt fica indistinguível de um caso mais difícil.
- **Custo e latência.** A meta da fase 1 é caso válido em menos de 60s. Com
  geração por LLM, cada caso reprovado pelo solver custa dinheiro e uma nova
  chamada.
- **Testabilidade.** RN-001 a RN-004 são invariantes estruturais. Se a
  estrutura vem de um modelo, testá-las exige chave de API no CI e aceita
  respostas diferentes a cada execução.

## Decisão

A estrutura é montada por um gerador determinístico com semente, em
`mansao.geracao.gerador`. O solver, em `mansao.geracao.solver`, recebe `Caso`
(nunca `CasoCompleto`) e tem poder de veto: caso não dedutível é descartado e
regerado com semente derivada.

O LLM entra **depois** da aprovação do solver e só escreve texto: nomes,
personalidade, descrição de cena, fala. Ele não pode criar, remover ou
reatribuir fato, escopo, posição na linha do tempo ou culpado.

Mesma semente e mesma versão do gerador produzem exatamente o mesmo caso.
`Caso.versao_gerador` acompanha o dado porque mudar o gerador muda o
significado da semente.

## Consequências

+ Toda a fase 1 roda sem chave de API: sem custo, sem rede, sem flakiness.
+ RN-001 a RN-004 viram testes de propriedade sobre dezenas de sementes.
+ O eval ganha um chão fixo: o mesmo caso em todas as execuções, então a
  variação medida é do modelo, não do mistério.
+ O solver vira verificador independente de verdade — ele não vê a solução, e a
  assinatura da função é a garantia disso, não a disciplina de quem escreve.
+ Geração em ~0,2 ms por caso, contra um alvo de 60s.
− A variedade fica limitada ao espaço de restrições que o código conhece. Casos
  vão parecer estruturalmente parecidos até esse espaço crescer.
− O gerador acumula complexidade combinatória que um prompt resolveria em três
  frases; cada tipo novo de pista é código, não texto.
− O verniz precisa de uma fronteira vigiada: um LLM que reescreve descrição pode
  contradizer a estrutura sem perceber. Vai exigir validação pós-verniz
  comparando fato a fato.

## Alternativas consideradas

- **LLM gera o caso inteiro como JSON estruturado, solver reprova e regera.** É
  literalmente o que RN-002 descreve, e dá variedade narrativa desde o primeiro
  dia. Rejeitada por reprodutibilidade: sem caso fixo, o eval de prompt mede
  duas variáveis ao mesmo tempo. Continua sendo o caminho natural se a
  monotonia estrutural virar o problema dominante — seria uma ADR nova, não um
  ajuste.
- **Híbrido: LLM propõe o tema, código converte em restrições.** Junta os dois
  mundos, ao custo de um schema para o briefing, um tradutor tema→restrições e
  um caminho de fallback quando o tema não couber. Complexidade cedo demais
  para um espaço de restrições que ainda é pequeno.
