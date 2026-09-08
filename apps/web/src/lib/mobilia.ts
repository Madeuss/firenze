/**
 * O que existe dentro de cada cômodo, e em que altura ele fica.
 *
 * Isto é **conteúdo do cenário**, não do jogo: são os móveis da mansão, e um
 * segundo cenário traria outros ids e outra lista. Fica no front, e não na
 * API, porque a API descreve a partida — quem esteve onde, o que se sabe — e
 * não o desenho dela. Cômodo sem entrada aqui simplesmente aparece vazio, que
 * é o comportamento certo para um cenário que ainda não foi mobiliado.
 *
 * As posições são frações do lado do cômodo, então mudar a escala da planta
 * não desarruma nada.
 */

export type Movel = {
  forma: 'caixa' | 'cilindro'
  /** Fração do lado do cômodo, a partir do centro. */
  em: [number, number]
  /** Largura, altura e fundo, também em frações do lado. */
  tamanho: [number, number, number]
  /** Quanto mais alto, mais claro. Madeira velha à luz de vela. */
  tom: number
}

// Larga o bastante para ler como estante, estreita o bastante para caber entre
// as paredes: o limite util e 0.436 do lado, descontada a espessura delas.
const ESTANTE = (x: number, z: number): Movel => ({
  forma: 'caixa',
  em: [x, z],
  tamanho: [0.34, 0.5, 0.12],
  tom: 0.5,
})

const BARRIL = (x: number, z: number): Movel => ({
  forma: 'cilindro',
  em: [x, z],
  tamanho: [0.15, 0.26, 0.15],
  tom: 0.42,
})

const CAIXOTE = (x: number, z: number, alto: number): Movel => ({
  forma: 'caixa',
  em: [x, z],
  tamanho: [0.22, alto, 0.22],
  tom: 0.38,
})

/**
 * Móveis por cômodo. Dois ou três bastam: o objetivo é a silhueta ser
 * reconhecível antes de alguém ler o rótulo, não decorar a casa.
 */
export const MOBILIA: Record<string, Movel[]> = {
  library: [
    ESTANTE(-0.2, -0.35),
    ESTANTE(0.2, -0.35),
    { forma: 'caixa', em: [0, 0.15], tamanho: [0.34, 0.13, 0.34], tom: 0.46 },
  ],
  parlour: [
    { forma: 'caixa', em: [-0.02, -0.3], tamanho: [0.6, 0.17, 0.2], tom: 0.5 },
    { forma: 'caixa', em: [0, 0.08], tamanho: [0.3, 0.08, 0.18], tom: 0.44 },
    { forma: 'cilindro', em: [0.34, 0.3], tamanho: [0.09, 0.3, 0.09], tom: 0.6 },
  ],
  dining_room: [
    { forma: 'caixa', em: [0, 0], tamanho: [0.66, 0.14, 0.26], tom: 0.5 },
    CAIXOTE(-0.24, -0.28, 0.16),
    CAIXOTE(0.24, -0.28, 0.16),
    CAIXOTE(-0.24, 0.28, 0.16),
    CAIXOTE(0.24, 0.28, 0.16),
  ],
  kitchen: [
    { forma: 'caixa', em: [0, -0.34], tamanho: [0.7, 0.2, 0.18], tom: 0.46 },
    { forma: 'caixa', em: [-0.3, 0.22], tamanho: [0.24, 0.26, 0.24], tom: 0.36 },
    { forma: 'caixa', em: [0.2, 0.24], tamanho: [0.38, 0.12, 0.24], tom: 0.5 },
  ],
  cellar: [
    BARRIL(-0.3, -0.28),
    BARRIL(-0.3, 0.04),
    BARRIL(0.02, -0.28),
    ESTANTE(0.24, 0.32),
  ],
  study: [
    { forma: 'caixa', em: [0, -0.16], tamanho: [0.5, 0.16, 0.26], tom: 0.5 },
    CAIXOTE(0, 0.18, 0.18),
    ESTANTE(-0.22, -0.35),
  ],
  conservatory: [
    { forma: 'cilindro', em: [-0.32, -0.3], tamanho: [0.13, 0.2, 0.13], tom: 0.44 },
    { forma: 'cilindro', em: [0.3, -0.3], tamanho: [0.13, 0.2, 0.13], tom: 0.44 },
    { forma: 'cilindro', em: [-0.3, 0.3], tamanho: [0.13, 0.2, 0.13], tom: 0.44 },
    { forma: 'caixa', em: [0.1, 0.24], tamanho: [0.4, 0.09, 0.15], tom: 0.54 },
  ],
  basement: [
    CAIXOTE(-0.26, -0.24, 0.3),
    CAIXOTE(-0.26, -0.24, 0.12),
    CAIXOTE(0.24, 0.1, 0.24),
    CAIXOTE(-0.02, 0.32, 0.18),
  ],
}

/**
 * Em que andar o cômodo fica. Zero é o térreo; negativo desce.
 *
 * Adega e porão descem um degrau, e isso não é só enfeite: são justamente dois
 * dos cômodos discretos onde os inocentes escondem o que escondem (RN-003). A
 * planta passa a dizer, sem texto, por que aquelas partes da casa servem para
 * sumir.
 */
export const DEGRAU: Record<string, number> = {
  cellar: -1,
  basement: -1,
}

export function moveisDe(comodo: string): Movel[] {
  return MOBILIA[comodo] ?? []
}

export function degrauDe(comodo: string): number {
  return DEGRAU[comodo] ?? 0
}
