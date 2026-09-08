/**
 * Confere a mobília da planta sem abrir um navegador.
 *
 * Três coisas que só se vê renderizando — e eu não tenho como renderizar aqui,
 * então elas viram aritmética. Todas já aconteceram de verdade: estantes
 * atravessando parede, uma lareira dentro de uma poltrona, e prateleiras três
 * vezes mais altas que a parede do cômodo.
 *
 *   node scripts/conferir-mobilia.mjs
 *
 * Lê `src/lib/mobilia.ts` como texto em vez de importar: o arquivo é
 * TypeScript e este script roda em node puro, sem etapa de build. O que ele
 * extrai são duas tabelas de dados literais, então o custo é baixo e o ganho é
 * a conferência rodar no CI junto com o resto.
 */

import { readFileSync } from 'node:fs'

// Precisam bater com as constantes de Planta.tsx.
const LADO = 2.2
const PAREDE_ESPESSURA = 0.14
const PAREDE_ALTURA = 0.34
const ALTURA_MAXIMA = PAREDE_ALTURA * 2

const util = LADO / 2 - PAREDE_ESPESSURA
const fonte = readFileSync(new URL('../src/lib/mobilia.ts', import.meta.url), 'utf8')

function tabela(nome) {
  const inicio = fonte.indexOf(`export const ${nome}`)
  if (inicio < 0) throw new Error(`${nome} não encontrada em mobilia.ts`)
  const abre = fonte.indexOf('= {', inicio) + 2
  let profundidade = 0
  let i = abre
  do {
    if (fonte[i] === '{') profundidade++
    if (fonte[i] === '}') profundidade--
    i++
  } while (profundidade > 0)
  return eval(`(${fonte.slice(abre, i)})`)
}

const VULTO = tabela('VULTO')
const MOBILIA = tabela('MOBILIA')

function caixa(movel) {
  const vulto = VULTO[movel.especie]
  if (!vulto) throw new Error(`espécie sem vulto: ${movel.especie}`)
  const escala = movel.escala ?? 1
  const girado = ((movel.giro ?? 0) % 2) === 1
  const largura = (girado ? vulto.fundo : vulto.largura) * escala * LADO
  const fundo = (girado ? vulto.largura : vulto.fundo) * escala * LADO
  const altura = vulto.altura * escala * LADO
  const x = movel.em[0] * LADO
  const z = movel.em[1] * LADO
  const y = (movel.sobre ?? 0) * LADO
  return {
    x0: x - largura / 2,
    x1: x + largura / 2,
    z0: z - fundo / 2,
    z1: z + fundo / 2,
    y0: y,
    y1: y + altura,
    altura,
  }
}

const queixas = []

for (const [comodo, moveis] of Object.entries(MOBILIA)) {
  const caixas = moveis.map(caixa)

  caixas.forEach((c, i) => {
    const especie = moveis[i].especie

    const estoura =
      Math.max(Math.abs(c.x0), Math.abs(c.x1)) > util ||
      Math.max(Math.abs(c.z0), Math.abs(c.z1)) > util
    if (estoura) queixas.push(`${comodo}: ${especie} atravessa a parede`)

    if (c.altura > ALTURA_MAXIMA) {
      queixas.push(
        `${comodo}: ${especie} tem ${c.altura.toFixed(2)} de altura, mais que o` +
          ` dobro da parede (${PAREDE_ALTURA}) — o cômodo vira poço`,
      )
    }

    for (let j = i + 1; j < caixas.length; j++) {
      const o = caixas[j]
      // Empilhar é legítimo, e é como os caixotes do porão existem: só colide
      // o que se cruza nos três eixos.
      const cruza =
        c.x0 < o.x1 &&
        o.x0 < c.x1 &&
        c.z0 < o.z1 &&
        o.z0 < c.z1 &&
        c.y0 < o.y1 - 0.01 &&
        o.y0 < c.y1 - 0.01
      if (cruza) {
        queixas.push(`${comodo}: ${especie} dentro de ${moveis[j].especie}`)
      }
    }
  })
}

const total = Object.values(MOBILIA).reduce((s, m) => s + m.length, 0)

if (queixas.length) {
  for (const queixa of queixas) console.error(`  ${queixa}`)
  console.error(`\n${queixas.length} problema(s) em ${total} móveis`)
  process.exit(1)
}

console.log(
  `${total} móveis em ${Object.keys(MOBILIA).length} cômodos: nenhum atravessa` +
    ` parede, nenhum dentro de outro, nenhum alto demais`,
)
