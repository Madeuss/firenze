'use client'

/**
 * Como cada móvel se parece.
 *
 * A primeira versão desenhava cada móvel como uma caixa maciça, e o resultado
 * foi um cômodo cheio de blocos que não pareciam nada. Uma mesa é um tampo com
 * quatro pernas — e é a perna, o vão embaixo dela, que faz o olho reconhecer
 * mesa. Então aqui cada espécie é uma pequena montagem de primitivas, e a
 * tabela em `mobilia.ts` diz só o que a coisa é.
 *
 * Continua sem asset importado. Existem kits prontos e de boa licença por aí,
 * mas são low-poly moderno e brigariam com o pixel art de época dos retratos —
 * e nenhum deles se ajusta sozinho ao tamanho do cômodo.
 */

import { useMemo } from 'react'

import { moveisDe, VULTO, type Especie, type Movel } from '@/lib/mobilia'

const MADEIRA = '#6d5c46'
const MADEIRA_CLARA = '#7f6d53'
const MADEIRA_ESCURA = '#54462f'
const FERRO = '#3b3a38'
const FOLHA = '#4d6350'
const ESTOFADO = '#5b4b4a'

/** Uma peça de madeira. Tudo aqui é caixa; o que muda é a proporção. */
function Tabua({
  em,
  tamanho,
  cor = MADEIRA,
}: {
  em: [number, number, number]
  tamanho: [number, number, number]
  cor?: string
}) {
  return (
    <mesh position={em} castShadow receiveShadow>
      <boxGeometry args={tamanho} />
      <meshLambertMaterial color={cor} />
    </mesh>
  )
}

function Pernas({
  largura,
  fundo,
  altura,
  grossura = 0.03,
  cor = MADEIRA_ESCURA,
}: {
  largura: number
  fundo: number
  altura: number
  grossura?: number
  cor?: string
}) {
  const x = largura / 2 - grossura
  const z = fundo / 2 - grossura
  return (
    <>
      {[
        [-x, -z],
        [x, -z],
        [-x, z],
        [x, z],
      ].map(([px, pz], i) => (
        <Tabua
          key={i}
          em={[px ?? 0, altura / 2, pz ?? 0]}
          tamanho={[grossura * 2, altura, grossura * 2]}
          cor={cor}
        />
      ))}
    </>
  )
}

function Mesa({ l, a, f }: { l: number; a: number; f: number }) {
  const tampo = 0.05 * (a / 0.17)
  return (
    <>
      <Pernas largura={l} fundo={f} altura={a - tampo} />
      <Tabua em={[0, a - tampo / 2, 0]} tamanho={[l, tampo, f]} cor={MADEIRA_CLARA} />
    </>
  )
}

function Cadeira({ l, a, f }: { l: number; a: number; f: number }) {
  const assento = a * 0.5
  return (
    <>
      <Pernas largura={l} fundo={f} altura={assento} grossura={0.018} />
      <Tabua em={[0, assento, 0]} tamanho={[l, 0.035, f]} cor={MADEIRA_CLARA} />
      <Tabua
        em={[0, assento + (a - assento) / 2, -f / 2 + 0.02]}
        tamanho={[l, a - assento, 0.035]}
      />
    </>
  )
}

/** Fundo, laterais e prateleiras: o vão entre elas é o que diz "estante". */
function Estante({ l, a, f }: { l: number; a: number; f: number }) {
  const prateleiras = 3
  return (
    <>
      <Tabua em={[0, a / 2, -f / 2]} tamanho={[l, a, 0.025]} cor={MADEIRA_ESCURA} />
      <Tabua em={[-l / 2, a / 2, 0]} tamanho={[0.03, a, f]} />
      <Tabua em={[l / 2, a / 2, 0]} tamanho={[0.03, a, f]} />
      {Array.from({ length: prateleiras }, (_, i) => (
        <Tabua
          key={i}
          em={[0, (a / prateleiras) * (i + 1) - 0.02, 0]}
          tamanho={[l, 0.03, f]}
          cor={MADEIRA_CLARA}
        />
      ))}
    </>
  )
}

function Poltrona({ l, a, f }: { l: number; a: number; f: number }) {
  const assento = a * 0.55
  return (
    <>
      <Tabua em={[0, assento / 2, 0]} tamanho={[l, assento, f]} cor={ESTOFADO} />
      <Tabua
        em={[0, a * 0.75, -f / 2 + 0.04]}
        tamanho={[l, a * 0.9, 0.08]}
        cor={ESTOFADO}
      />
      <Tabua em={[-l / 2 + 0.03, assento + 0.03, 0]} tamanho={[0.06, 0.08, f]} cor={ESTOFADO} />
      <Tabua em={[l / 2 - 0.03, assento + 0.03, 0]} tamanho={[0.06, 0.08, f]} cor={ESTOFADO} />
    </>
  )
}

function Barril({ l, a }: { l: number; a: number }) {
  return (
    <>
      <mesh position={[0, a / 2, 0]} castShadow receiveShadow>
        <cylinderGeometry args={[l / 2, l / 2.4, a, 14]} />
        <meshLambertMaterial color={MADEIRA} />
      </mesh>
      {[0.3, 0.72].map((h) => (
        <mesh key={h} position={[0, a * h, 0]}>
          <torusGeometry args={[l / 2 + 0.004, 0.012, 6, 16]} />
          <meshLambertMaterial color={FERRO} />
        </mesh>
      ))}
    </>
  )
}

/** Caixote é caixa — mas com as ripas aparecendo, senão vira cubo. */
function Caixote({ l, a, f }: { l: number; a: number; f: number }) {
  return (
    <>
      <Tabua em={[0, a / 2, 0]} tamanho={[l, a, f]} cor={MADEIRA_ESCURA} />
      <Tabua em={[0, a * 0.28, 0]} tamanho={[l + 0.01, 0.035, f + 0.01]} cor={MADEIRA_CLARA} />
      <Tabua em={[0, a * 0.78, 0]} tamanho={[l + 0.01, 0.035, f + 0.01]} cor={MADEIRA_CLARA} />
    </>
  )
}

function Vaso({ l, a }: { l: number; a: number }) {
  return (
    <>
      <mesh position={[0, a * 0.22, 0]} castShadow receiveShadow>
        <cylinderGeometry args={[l / 2, l / 2.8, a * 0.44, 12]} />
        <meshLambertMaterial color={MADEIRA_ESCURA} />
      </mesh>
      <mesh position={[0, a * 0.72, 0]} castShadow>
        <icosahedronGeometry args={[l * 0.55, 0]} />
        <meshLambertMaterial color={FOLHA} flatShading />
      </mesh>
    </>
  )
}

function Bancada({ l, a, f }: { l: number; a: number; f: number }) {
  return (
    <>
      <Tabua em={[0, a / 2, 0]} tamanho={[l, a, f]} cor={MADEIRA_ESCURA} />
      <Tabua em={[0, a + 0.02, 0]} tamanho={[l + 0.03, 0.04, f + 0.03]} cor={MADEIRA_CLARA} />
    </>
  )
}

function Fogao({ l, a, f }: { l: number; a: number; f: number }) {
  return (
    <>
      <Tabua em={[0, a / 2, 0]} tamanho={[l, a, f]} cor={FERRO} />
      <Tabua em={[0, a + 0.02, 0]} tamanho={[l + 0.02, 0.04, f + 0.02]} cor="#2b2a29" />
      <mesh position={[0, a + 0.16, -f / 2 + 0.04]} castShadow>
        <cylinderGeometry args={[0.035, 0.035, 0.3, 10]} />
        <meshLambertMaterial color={FERRO} />
      </mesh>
    </>
  )
}

function Escrivaninha({ l, a, f }: { l: number; a: number; f: number }) {
  const tampo = 0.05
  return (
    <>
      <Tabua em={[-l / 2 + 0.08, (a - tampo) / 2, 0]} tamanho={[0.16, a - tampo, f]} />
      <Tabua em={[l / 2 - 0.02, (a - tampo) / 2, -f / 2 + 0.03]} tamanho={[0.04, a - tampo, 0.04]} cor={MADEIRA_ESCURA} />
      <Tabua em={[l / 2 - 0.02, (a - tampo) / 2, f / 2 - 0.03]} tamanho={[0.04, a - tampo, 0.04]} cor={MADEIRA_ESCURA} />
      <Tabua em={[0, a - tampo / 2, 0]} tamanho={[l, tampo, f]} cor={MADEIRA_CLARA} />
    </>
  )
}

const DESENHO: Record<
  Especie,
  (m: { l: number; a: number; f: number }) => React.ReactElement
> = {
  mesa: Mesa,
  cadeira: Cadeira,
  estante: Estante,
  poltrona: Poltrona,
  barril: Barril,
  caixote: Caixote,
  vaso: Vaso,
  bancada: Bancada,
  fogao: Fogao,
  escrivaninha: Escrivaninha,
}

export default function Moveis({ comodo, lado }: { comodo: string; lado: number }) {
  const moveis = useMemo(() => moveisDe(comodo), [comodo])

  return (
    <>
      {moveis.map((movel: Movel, i) => {
        const vulto = VULTO[movel.especie]
        const escala = movel.escala ?? 1
        const Desenho = DESENHO[movel.especie]
        return (
          <group
            key={i}
            position={[movel.em[0] * lado, 0.11, movel.em[1] * lado]}
            rotation={[0, ((movel.giro ?? 0) * Math.PI) / 2, 0]}
          >
            <Desenho
              l={vulto.largura * lado * escala}
              a={vulto.altura * lado * escala}
              f={vulto.fundo * lado * escala}
            />
          </group>
        )
      })}
    </>
  )
}
