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
  /** Levanta o móvel, em frações do lado. É o que empilha um caixote no outro. */
  sobre?: number
}

/**
 * Quanto cada espécie ocupa no chão e quanto sobe, em frações do lado.
 *
 * Serve para o desenho e para a conferência: nada pode atravessar parede, e o
 * limite útil é metade do lado menos a espessura dela.
 */
export const VULTO: Record<
  Especie,
  { largura: number; altura: number; fundo: number }
> = {
  mesa: { largura: 0.5, altura: 0.13, fundo: 0.28 },
  cadeira: { largura: 0.15, altura: 0.16, fundo: 0.15 },
  estante: { largura: 0.3, altura: 0.26, fundo: 0.11 },
  poltrona: { largura: 0.26, altura: 0.14, fundo: 0.22 },
  barril: { largura: 0.16, altura: 0.17, fundo: 0.16 },
  caixote: { largura: 0.18, altura: 0.15, fundo: 0.18 },
  vaso: { largura: 0.14, altura: 0.18, fundo: 0.14 },
  bancada: { largura: 0.46, altura: 0.14, fundo: 0.16 },
  fogao: { largura: 0.2, altura: 0.18, fundo: 0.18 },
  escrivaninha: { largura: 0.38, altura: 0.14, fundo: 0.22 },
  lareira: { largura: 0.34, altura: 0.24, fundo: 0.14 },
}

export const MOBILIA: Record<string, Movel[]> = {
  library: [
    { especie: 'estante', em: [-0.19, -0.36] },
    { especie: 'estante', em: [0.19, -0.36] },
    { especie: 'poltrona', em: [-0.18, 0.22], giro: 2 },
    { especie: 'mesa', em: [0.22, 0.24], escala: 0.45 },
  ],
  parlour: [
    { especie: 'lareira', em: [0, -0.35] },
    { especie: 'poltrona', em: [-0.26, 0.0], giro: 1 },
    { especie: 'poltrona', em: [0.26, 0.0], giro: 3 },
    { especie: 'mesa', em: [0, 0.06], escala: 0.5 },
    { especie: 'vaso', em: [0.3, 0.32] },
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
    { especie: 'estante', em: [0, -0.36] },
    { especie: 'escrivaninha', em: [0, -0.05] },
    { especie: 'cadeira', em: [0, 0.24], giro: 2 },
  ],
  conservatory: [
    { especie: 'vaso', em: [-0.3, -0.28] },
    { especie: 'vaso', em: [0.3, -0.28] },
    { especie: 'vaso', em: [-0.28, 0.28] },
    { especie: 'poltrona', em: [0.14, 0.24], giro: 2 },
  ],
  basement: [
    { especie: 'caixote', em: [-0.26, -0.24] },
    { especie: 'caixote', em: [-0.26, -0.24], escala: 0.7, sobre: 0.15 },
    { especie: 'caixote', em: [0.24, 0.06] },
    { especie: 'caixote', em: [0.02, 0.3], escala: 0.8 },
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

/** A pegada do móvel no chão, em frações do lado, já contando o giro. */
export function pegadaDe(movel: Movel): {
  x0: number
  x1: number
  z0: number
  z1: number
} {
  const vulto = VULTO[movel.especie]
  const escala = movel.escala ?? 1
  const girado = ((movel.giro ?? 0) % 2) === 1
  const largura = (girado ? vulto.fundo : vulto.largura) * escala
  const fundo = (girado ? vulto.largura : vulto.fundo) * escala
  return {
    x0: movel.em[0] - largura / 2,
    x1: movel.em[0] + largura / 2,
    z0: movel.em[1] - fundo / 2,
    z1: movel.em[1] + fundo / 2,
  }
}

/**
 * Um ponto do cômodo onde cabe algo desse tamanho sem cair em cima de um móvel.
 *
 * Existe por causa da silhueta de giz: o corpo foi encontrado em algum lugar do
 * cômodo, e o centro — que era o óbvio — é exatamente onde ficam a mesa de
 * jantar e a escrivaninha do escritório. Varre uma grade do meio para fora e
 * devolve o primeiro lugar vago, então a marca fica o mais central que der.
 *
 * Devolve `null` quando o cômodo está cheio demais; quem chama decide o que
 * fazer com isso, e `scripts/conferir-mobilia.mjs` falha se acontecer.
 */
export function lugarLivre(
  comodo: string,
  largura: number,
  fundo: number,
): [number, number] | null {
  const pegadas = moveisDe(comodo).map(pegadaDe)
  const limiteX = 0.5 - 0.07 - largura / 2
  const limiteZ = 0.5 - 0.07 - fundo / 2
  const passo = 0.04

  const candidatos: [number, number][] = []
  for (let x = -limiteX; x <= limiteX + 1e-9; x += passo) {
    for (let z = -limiteZ; z <= limiteZ + 1e-9; z += passo) {
      candidatos.push([Number(x.toFixed(3)), Number(z.toFixed(3))])
    }
  }
  candidatos.sort((a, b) => a[0] ** 2 + a[1] ** 2 - (b[0] ** 2 + b[1] ** 2))

  for (const [x, z] of candidatos) {
    const livre = pegadas.every(
      (p) =>
        x + largura / 2 <= p.x0 ||
        p.x1 <= x - largura / 2 ||
        z + fundo / 2 <= p.z0 ||
        p.z1 <= z - fundo / 2,
    )
    if (livre) return [x, z]
  }
  return null
}

export function degrauDe(comodo: string): number {
  return DEGRAU[comodo] ?? 0
}
