/**
 * O token que prova que a partida é sua. (T-11)
 *
 * A API devolve um token uma única vez, ao criar a partida, e depois nunca
 * mais — não há conta de onde recuperá-lo. Quem o perde perde a partida, e é
 * esse o preço de um jogo que não pede login e por isso não guarda dado
 * pessoal nenhum.
 *
 * Por partida, e não um token só: assim abrir duas investigações em abas
 * diferentes continua funcionando, e apagar uma não derruba a outra.
 *
 * `localStorage` some em aba anônima e em navegador limpo. Isso é o
 * comportamento certo — a partida fica inacessível de verdade, inclusive para
 * quem pegou o link — e é por isso que a leitura tolera falha em silêncio em
 * vez de quebrar a tela.
 */

const PREFIXO = 'firenze.dono.'

export function guardarToken(partida: string, token: string): void {
  try {
    localStorage.setItem(PREFIXO + partida, token)
  } catch {
    // Navegador com armazenamento bloqueado: a partida corrente segue, porque
    // o token continua em memória enquanto a aba viver.
  }
  emMemoria.set(partida, token)
}

export function tokenDe(partida: string): string | null {
  const lembrado = emMemoria.get(partida)
  if (lembrado) return lembrado
  try {
    return localStorage.getItem(PREFIXO + partida)
  } catch {
    return null
  }
}

/** Sobrevive ao armazenamento bloqueado, não sobrevive ao recarregar. */
const emMemoria = new Map<string, string>()
