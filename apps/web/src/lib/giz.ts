/**
 * A silhueta de giz da perícia, desenhada em código.
 *
 * O losango branco que marcava o cômodo do crime dizia "aqui" e mais nada — e
 * um quadrado no chão é a mesma forma que o jogo usa para tudo. A silhueta diz
 * a mesma coisa e ainda diz *o quê*: alguém foi encontrado caído ali.
 *
 * É desenhada num canvas em vez de vir de arquivo por três motivos: não
 * depende de licença de terceiro (isto é feito aqui, não baixado), acompanha a
 * paleta porque a cor é parâmetro, e não pesa nada no bundle. Sai como textura
 * de um plano deitado no chão da planta.
 *
 * O traço é irregular de propósito: giz sobre assoalho não sai reto. A
 * irregularidade vem de um gerador com semente fixa, então a marca é a mesma
 * em toda partida — tremor que muda a cada quadro vira ruído, não textura.
 */

/** O contorno, em coordenadas de 0 a 512, no sentido horário a partir do pescoço. */
const CONTORNO: readonly (readonly [number, number])[] = [
  // pescoço e ombro esquerdos
  [220, 128],
  [180, 156],
  // braço esquerdo aberto, mão para fora
  [116, 152],
  [76, 180],
  [90, 204],
  [156, 192],
  // flanco e quadril esquerdos
  [184, 238],
  [172, 294],
  // perna esquerda
  [146, 376],
  [112, 462],
  [154, 480],
  [198, 392],
  // entrepernas
  [256, 332],
  // perna direita, jogada mais para fora
  [316, 380],
  [366, 466],
  [406, 448],
  [352, 362],
  // quadril e flanco direitos
  [342, 290],
  [328, 236],
  // braço direito, por baixo até a mão e de volta por cima
  [352, 198],
  [418, 206],
  [446, 188],
  [428, 160],
  [356, 158],
  [294, 156],
  // cabeça
  [292, 128],
  [308, 92],
  [296, 44],
  [256, 26],
  [216, 44],
  [204, 92],
]

/** Ruído com semente: a mesma marca em toda partida (ver o cabeçalho). */
function tremor(semente: number): () => number {
  let estado = semente
  return () => {
    estado = (estado * 1664525 + 1013904223) % 4294967296
    return estado / 4294967296 - 0.5
  }
}

/**
 * Curva fechada e suave pelos pontos, à la Catmull-Rom.
 *
 * Ligar os pontos com retas daria um polígono, e polígono não parece giz —
 * parece planta baixa, que é justamente o que esta marca precisa não ser.
 */
function tracar(
  ctx: CanvasRenderingContext2D,
  pontos: readonly (readonly [number, number])[],
  desvio: () => number,
  folga: number,
): void {
  const n = pontos.length
  // O desvio é sorteado uma vez por ponto, e não a cada leitura: o fim de um
  // trecho tem que ser exatamente o começo do próximo, ou o contorno se parte.
  const tremidos: [number, number][] = pontos.map(([x, y]) => [
    x + desvio() * folga,
    y + desvio() * folga,
  ])
  // O índice é sempre normalizado para dentro da lista; o `!` diz isso ao
  // TypeScript, que não tem como saber.
  const em = (i: number): [number, number] => tremidos[((i % n) + n) % n]!

  ctx.beginPath()
  const [x0, y0] = em(0)
  ctx.moveTo(x0, y0)
  for (let i = 0; i < n; i++) {
    const [ax, ay] = em(i - 1)
    const [bx, by] = em(i)
    const [cx, cy] = em(i + 1)
    const [dx, dy] = em(i + 2)
    ctx.bezierCurveTo(
      bx + (cx - ax) / 6,
      by + (cy - ay) / 6,
      cx - (dx - bx) / 6,
      cy - (dy - by) / 6,
      cx,
      cy,
    )
  }
  ctx.closePath()
  ctx.stroke()
}

/**
 * A silhueta num canvas quadrado, transparente fora do traço.
 *
 * Só roda no navegador: quem chama monta a textura depois da montagem do
 * componente, porque no servidor não existe canvas.
 */
export function silhuetaDeGiz(cor = '#f5efe2', lado = 512): HTMLCanvasElement {
  const canvas = document.createElement('canvas')
  canvas.width = lado
  canvas.height = lado
  const ctx = canvas.getContext('2d')
  if (!ctx) return canvas

  const escala = lado / 512
  ctx.scale(escala, escala)
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  ctx.strokeStyle = cor

  // Três passadas: uma grossa e apagada por baixo, que é o pó, e duas finas
  // por cima com desvios diferentes, que é o traço.
  const passadas = [
    { largura: 13, alfa: 0.2, folga: 5, semente: 7 },
    { largura: 6, alfa: 0.95, folga: 2.5, semente: 101 },
    { largura: 3.5, alfa: 0.6, folga: 4, semente: 991 },
  ]
  for (const passada of passadas) {
    ctx.globalAlpha = passada.alfa
    ctx.lineWidth = passada.largura
    tracar(ctx, CONTORNO, tremor(passada.semente), passada.folga)
  }

  return canvas
}
