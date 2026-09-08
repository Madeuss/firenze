/**
 * As anotações do jogador sobre quem esteve onde.
 *
 * Elas são **dele**, não do servidor. A API entrega a casa e a noite e nada
 * sobre quem alegou o quê: reconstruir a noite a partir das respostas é a
 * dedução, e servidor que entrega planta preenchida resolve o jogo
 * (docs/03-casos-de-uso.md §2).
 *
 * Ficam no navegador porque guardar no servidor exige antes decidir de quem é
 * a partida, e nada autentica uma hoje — T-11 em docs/05-threat-model.md. A
 * ordem certa é resolver a posse antes de guardar o que alguém escreveu.
 *
 * ## Por que uma store e não `useState` mais um efeito
 *
 * `localStorage` não existe no servidor, então a primeira renderização tem que
 * ser vazia dos dois lados ou a hidratação quebra. Carregar num efeito e
 * chamar `setState` resolve, e é exatamente o que React 19 pede para não
 * fazer — render em cascata. `useSyncExternalStore` é a porta certa: o
 * navegador tem um instantâneo, o servidor tem outro, e ninguém precisa de
 * efeito nenhum.
 */

export type Notas = Record<string, Record<number, string>>

const CHAVE = 'firenze:notas:'
const VAZIO: Notas = {}

// O instantâneo precisa ser estável entre chamadas, senão `useSyncExternalStore`
// re-renderiza para sempre. Daí o cache por partida.
const cache = new Map<string, Notas>()
const ouvintes = new Set<() => void>()

function ler(partida: string): Notas {
  try {
    const cru = window.localStorage.getItem(CHAVE + partida)
    return cru ? (JSON.parse(cru) as Notas) : VAZIO
  } catch {
    // Aba anônima, armazenamento cheio, permissão negada: o caderno mental
    // some, o jogo continua. Nada aqui é dado que a partida precise.
    return VAZIO
  }
}

export function assinar(ouvinte: () => void): () => void {
  ouvintes.add(ouvinte)
  return () => ouvintes.delete(ouvinte)
}

export function instantaneo(partida: string): Notas {
  let atual = cache.get(partida)
  if (!atual) {
    atual = ler(partida)
    cache.set(partida, atual)
  }
  return atual
}

export function instantaneoDoServidor(): Notas {
  return VAZIO
}

export function escrever(partida: string, notas: Notas): void {
  cache.set(partida, notas)
  try {
    window.localStorage.setItem(CHAVE + partida, JSON.stringify(notas))
  } catch {
    // idem: o jogo não depende disto
  }
  for (const ouvinte of ouvintes) ouvinte()
}

export function anotar(
  notas: Notas,
  suspeito: string,
  hora: number,
  comodo: string | null,
): Notas {
  const doSuspeito = { ...(notas[suspeito] ?? {}) }
  if (comodo === null) delete doSuspeito[hora]
  else doSuspeito[hora] = comodo
  return { ...notas, [suspeito]: doSuspeito }
}

export function onde(
  notas: Notas,
  suspeito: string,
  hora: number,
): string | null {
  return notas[suspeito]?.[hora] ?? null
}

/**
 * Onde duas anotações se chocam: mesmo cômodo, mesma hora, gente diferente.
 *
 * Não é erro do jogador nem do jogo — é o achado. Duas pessoas dizendo que
 * estavam no escritório às 22h30 significa que pelo menos uma mentiu, e é
 * disso que sai o confronto. Por isso o choque acende em vez de ser impedido.
 */
export function choques(notas: Notas, hora: number): Set<string> {
  const porComodo = new Map<string, number>()
  for (const suspeito of Object.keys(notas)) {
    const comodo = onde(notas, suspeito, hora)
    if (comodo) porComodo.set(comodo, (porComodo.get(comodo) ?? 0) + 1)
  }
  return new Set(
    [...porComodo].filter(([, quantos]) => quantos > 1).map(([c]) => c),
  )
}
