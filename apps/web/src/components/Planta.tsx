'use client'

/**
 * A planta da casa, isométrica, com a noite raspável.
 *
 * Câmera **ortográfica** e fixa: sem perspectiva e sem órbita. As duas coisas
 * são de propósito — perspectiva faria cômodos do fundo parecerem menores que
 * os da frente, e num tabuleiro onde o jogador compara posições isso engana; e
 * câmera livre transformaria "achar o escritório" numa tarefa de pilotagem.
 *
 * A geometria toda sai dos dados: a API devolve os cômodos e as horas, e nada
 * mais. Nenhum modelo importado, nenhuma textura — são blocos, e a arte está na
 * luz e na paleta.
 */

import { Canvas, useThree, type ThreeEvent } from '@react-three/fiber'
import { useEffect, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'

import type { FloorPlan } from '@/lib/api'

import styles from './Planta.module.css'

const NOITE = '#14161f'
const PISO = '#2c3040'
const PISO_ALVO = '#3b4257'
const OSSO = '#f5efe2'
const ALARME = '#c05f47'

const LADO = 2.2 // do cômodo
const VAO = 0.35 // entre um cômodo e outro
const COLUNAS = 4

/** Onde cada cômodo fica no tabuleiro. A API dá a lista, não o desenho. */
function assentar(comodos: readonly string[]): Map<string, [number, number]> {
  const linhas = Math.ceil(comodos.length / COLUNAS)
  const passo = LADO + VAO
  return new Map(
    comodos.map((id, i) => {
      const coluna = i % COLUNAS
      const linha = Math.floor(i / COLUNAS)
      return [
        id,
        [
          (coluna - (COLUNAS - 1) / 2) * passo,
          (linha - (linhas - 1) / 2) * passo,
        ] as [number, number],
      ]
    }),
  )
}

/** Iniciais numa textura, que é como um bloco carrega um nome. */
function selo(texto: string): THREE.CanvasTexture {
  const lado = 128
  const tela = document.createElement('canvas')
  tela.width = tela.height = lado
  const pincel = tela.getContext('2d')
  if (pincel) {
    pincel.fillStyle = 'rgba(0,0,0,0)'
    pincel.fillRect(0, 0, lado, lado)
    pincel.fillStyle = NOITE
    pincel.font = '600 58px system-ui, sans-serif'
    pincel.textAlign = 'center'
    pincel.textBaseline = 'middle'
    pincel.fillText(texto, lado / 2, lado / 2 + 4)
  }
  const textura = new THREE.CanvasTexture(tela)
  textura.colorSpace = THREE.SRGBColorSpace
  return textura
}

function Comodo({
  posicao,
  aceso,
  emChoque,
  aoClicar,
}: {
  posicao: [number, number]
  aceso: boolean
  emChoque: boolean
  aoClicar: () => void
}) {
  const [sobre, setSobre] = useState(false)
  const cor = emChoque ? ALARME : aceso || sobre ? PISO_ALVO : PISO

  return (
    <mesh
      position={[posicao[0], 0, posicao[1]]}
      onClick={(evento: ThreeEvent<MouseEvent>) => {
        evento.stopPropagation()
        aoClicar()
      }}
      onPointerOver={() => setSobre(true)}
      onPointerOut={() => setSobre(false)}
      receiveShadow
    >
      <boxGeometry args={[LADO, 0.25, LADO]} />
      <meshLambertMaterial color={cor} />
    </mesh>
  )
}

/** Um suspeito onde o jogador o colocou. */
function Peca({
  posicao,
  iniciais,
  destacado,
}: {
  posicao: [number, number]
  iniciais: string
  destacado: boolean
}) {
  const textura = useMemo(() => selo(iniciais), [iniciais])
  useEffect(() => () => textura.dispose(), [textura])

  return (
    <group position={[posicao[0], 0.42, posicao[1]]}>
      <mesh castShadow>
        <cylinderGeometry args={[0.42, 0.42, 0.3, 24]} />
        <meshLambertMaterial color={destacado ? OSSO : '#9a9384'} />
      </mesh>
      <mesh position={[0, 0.16, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[0.62, 0.62]} />
        <meshBasicMaterial map={textura} transparent />
      </mesh>
    </group>
  )
}

/** Projeta os centros dos cômodos na tela, uma vez: a câmera não se move. */
function Rotulos({
  assento,
  nomes,
  aoMedir,
}: {
  assento: Map<string, [number, number]>
  nomes: Map<string, string>
  aoMedir: (pontos: { id: string; nome: string; x: number; y: number }[]) => void
}) {
  const { camera, size } = useThree()

  useEffect(() => {
    const pontos = [...assento].map(([id, [x, z]]) => {
      const v = new THREE.Vector3(x, 0.14, z + LADO / 2 - 0.2).project(camera)
      return {
        id,
        nome: nomes.get(id) ?? id,
        x: ((v.x + 1) / 2) * size.width,
        y: ((1 - v.y) / 2) * size.height,
      }
    })
    aoMedir(pontos)
  }, [assento, nomes, camera, size, aoMedir])

  return null
}

export default function Planta({
  plan,
  hora,
  pecas,
  emChoque,
  selecionado,
  aoEscolherComodo,
}: {
  plan: FloorPlan
  hora: number
  /** Quem está em cada cômodo nesta hora, já resolvido pelo pai. */
  pecas: { comodo: string; iniciais: string; destacado: boolean }[]
  emChoque: Set<string>
  selecionado: string | null
  aoEscolherComodo: (comodo: string) => void
}) {
  const comodos = useMemo(() => plan.rooms.map((r) => r.id), [plan])
  const assento = useMemo(() => assentar(comodos), [comodos])
  const nomes = useMemo(
    () => new Map(plan.rooms.map((r) => [r.id, r.name])),
    [plan],
  )
  const [rotulos, setRotulos] = useState<
    { id: string; nome: string; x: number; y: number }[]
  >([])
  const medido = useRef(false)

  return (
    <div className={styles.palco}>
      <Canvas
        orthographic
        shadows
        camera={{ position: [9, 9, 9], zoom: 62, near: -50, far: 100 }}
        style={{ background: NOITE }}
      >
        <ambientLight intensity={1.1} />
        {/* Uma luz só, vinda de onde vem a luz nos retratos: da esquerda. */}
        <directionalLight position={[-6, 10, 4]} intensity={2.2} castShadow />

        {[...assento].map(([id, posicao]) => (
          <Comodo
            key={id}
            posicao={posicao}
            aceso={selecionado === id}
            emChoque={emChoque.has(id)}
            aoClicar={() => aoEscolherComodo(id)}
          />
        ))}

        {pecas.map((peca, i) => {
          const base = assento.get(peca.comodo)
          if (!base) return null
          // Duas pessoas no mesmo cômodo não podem ficar uma dentro da outra —
          // é justamente o caso que interessa ver.
          const desvio = (i % 3) * 0.5 - 0.5
          return (
            <Peca
              key={`${peca.comodo}-${peca.iniciais}-${hora}`}
              posicao={[base[0] + desvio, base[1] + desvio * 0.4]}
              iniciais={peca.iniciais}
              destacado={peca.destacado}
            />
          )
        })}

        <Rotulos
          assento={assento}
          nomes={nomes}
          aoMedir={(pontos) => {
            if (medido.current) return
            medido.current = true
            setRotulos(pontos)
          }}
        />
      </Canvas>

      {rotulos.map((rotulo) => (
        <span
          key={rotulo.id}
          className={emChoque.has(rotulo.id) ? styles.rotuloAceso : styles.rotulo}
          style={{ left: rotulo.x, top: rotulo.y }}
        >
          {rotulo.nome}
        </span>
      ))}
    </div>
  )
}
