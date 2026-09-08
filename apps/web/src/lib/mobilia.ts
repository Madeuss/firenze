/**
 * O que existe dentro de cada cômodo, e em que altura ele fica.
 *
 * Isto é **conteúdo do cenário**, não do jogo: são os móveis da mansão, e um
 * segundo cenário traria outros ids e outra lista. Fica no front, e não na
 * API, porque a API descreve a partida — quem esteve onde, o que se sabe — e
 * não o desenho dela. Cômodo sem entrada aqui simplesmente aparece vazio, que
 * é o comportamento certo para um cenário que ainda não foi mobiliado.
 *
 * A tabela diz **o que** o móvel é e onde ele fica; como ele se parece é com o
 * componente que desenha. A primeira versão guardava caixas com medidas, e o
 * resultado foi um cômodo cheio de blocos que não pareciam nada — hoje quase
 * tudo vem de modelo, e o que sobrou de primitiva é o que o pacote não tinha.
 *
 * O `VULTO` continua sendo medida de dado, e não de desenho: é o espaço que a
 * espécie tem direito de ocupar. O modelo é encolhido até caber nele, e é isso
 * que garante que nada atravesse parede por mais que o arquivo mude.
 *
 * As posições são frações do lado do cômodo, então mudar a escala da planta
 * não desarruma nada.
 */

export type Especie =
  | 'mesa'
  | 'cadeira'
  | 'estante'
  | 'poltrona'
  | 'barril'
  | 'caixote'
  | 'vaso'
  | 'bancada'
  | 'fogao'
  | 'escrivaninha'
  | 'lareira'

export type Movel = {
  especie: Especie
  /** Fração do lado do cômodo, a partir do centro. */
  em: [number, number]
  /** Quartos de volta. Uma cadeira encostada na mesa olha para ela. */
  giro?: number
  /** Multiplica o tamanho padrão da espécie. */
  escala?: number
}

/**
 * Quanto cada espécie ocupa no chão e quanto sobe, em frações do lado.
 *
 * Serve para o desenho e para a conferência: nada pode atravessar parede, e o
 * limite útil é metade do lado menos a espessura dela.
 */
export const VULTO: Record<Especie, { largura: number; altura: number; fundo: number }> = {
  mesa: { largura: 0.62, altura: 0.17, fundo: 0.3 },
  cadeira: { largura: 0.16, altura: 0.3, fundo: 0.16 },
  estante: { largura: 0.34, altura: 0.5, fundo: 0.12 },
  poltrona: { largura: 0.3, altura: 0.22, fundo: 0.24 },
  barril: { largura: 0.17, altura: 0.24, fundo: 0.17 },
  caixote: { largura: 0.2, altura: 0.2, fundo: 0.2 },
  vaso: { largura: 0.16, altura: 0.3, fundo: 0.16 },
  bancada: { largura: 0.55, altura: 0.2, fundo: 0.18 },
  fogao: { largura: 0.24, altura: 0.26, fundo: 0.22 },
  escrivaninha: { largura: 0.44, altura: 0.18, fundo: 0.24 },
  lareira: { largura: 0.4, altura: 0.34, fundo: 0.16 },
}

export const MOBILIA: Record<string, Movel[]> = {
  library: [
    { especie: 'estante', em: [-0.2, -0.34] },
    { especie: 'estante', em: [0.2, -0.34] },
    { especie: 'poltrona', em: [-0.16, 0.2], giro: 2 },
    { especie: 'mesa', em: [0.18, 0.22], escala: 0.5 },
  ],
  parlour: [
    { especie: 'poltrona', em: [-0.22, -0.24] },
    { especie: 'poltrona', em: [0.22, -0.24] },
    { especie: 'mesa', em: [0, 0.06], escala: 0.55 },
    { especie: 'vaso', em: [0.28, 0.3] },
    { especie: 'lareira', em: [0, -0.33] },
  ],
  dining_room: [
    { especie: 'mesa', em: [0, 0] },
    { especie: 'cadeira', em: [-0.2, -0.28] },
    { especie: 'cadeira', em: [0.2, -0.28] },
    { especie: 'cadeira', em: [-0.2, 0.28], giro: 2 },
    { especie: 'cadeira', em: [0.2, 0.28], giro: 2 },
  ],
  kitchen: [
    { especie: 'bancada', em: [0, -0.3] },
    { especie: 'fogao', em: [-0.28, 0.24] },
    { especie: 'mesa', em: [0.16, 0.24], escala: 0.6 },
  ],
  cellar: [
    { especie: 'barril', em: [-0.28, -0.26] },
    { especie: 'barril', em: [-0.28, 0.06] },
    { especie: 'barril', em: [0.02, -0.28] },
    { especie: 'estante', em: [0.22, 0.3], giro: 2 },
  ],
  study: [
    { especie: 'escrivaninha', em: [0, -0.14] },
    { especie: 'cadeira', em: [0, 0.18], giro: 2 },
    { especie: 'estante', em: [-0.22, -0.34] },
  ],
  conservatory: [
    { especie: 'vaso', em: [-0.3, -0.28] },
    { especie: 'vaso', em: [0.3, -0.28] },
    { especie: 'vaso', em: [-0.28, 0.28] },
    { especie: 'poltrona', em: [0.14, 0.24], giro: 2 },
  ],
  basement: [
    { especie: 'caixote', em: [-0.26, -0.24] },
    { especie: 'caixote', em: [-0.26, -0.24], escala: 0.6 },
    { especie: 'caixote', em: [0.24, 0.08] },
    { especie: 'caixote', em: [-0.02, 0.3], escala: 0.8 },
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
