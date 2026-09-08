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
 * mais. Nenhum modelo importado — são caixas, e a arte está na luz, nas
 * paredes e na paleta.
 */

import { Canvas, useThree, type ThreeEvent } from '@react-three/fiber'
import { useEffect, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'

import type { FloorPlan } from '@/lib/api'
import { retratoDe } from '@/lib/retratos'

import styles from './Planta.module.css'

const NOITE = '#14161f'
const PISO = '#262a38'
const PISO_ALVO = '#3b4257'
const PAREDE = '#1c2030'
const PAREDE_ALTA = '#39405a'
const OSSO = '#f5efe2'
const ALARME = '#c05f47'

const LADO = 2.2
const VAO = 0.5
const COLUNAS = 4
const PAREDE_ALTURA = 0.34
const PAREDE_ESPESSURA = 0.14

export type Peca = {
  suspeito: string
  nome: string
  comodo: string
  destacado: boolean
}

function assentar(comodos: readonly string[]): Map<string, [number, number]> {
  const linhas = Math.ceil(comodos.length / COLUNAS)
  const passo = LADO + VAO
  return new Map(
    comodos.map((id, i) => [
      id,
      [
        ((i % COLUNAS) - (COLUNAS - 1) / 2) * passo,
        (Math.floor(i / COLUNAS) - (linhas - 1) / 2) * passo,
      ] as [number, number],
    ]),
  )
}

/**
 * Onde cada peça fica dentro do cômodo.
 *
 * Nada impede quatro pessoas no mesmo lugar — e a versão anterior empilhava
 * todas na diagonal, o que virava um borrão justamente no caso que mais
 * interessa ver. Aqui elas entram numa grade que cresce com a quantidade, e
 * encolhem juntas para continuarem cabendo.
 */
function arrumar(quantas: number): { grade: number; escala: number } {
  const grade = Math.ceil(Math.sqrt(quantas))
  return { grade, escala: Math.min(1, 2.1 / grade) }
}

function Comodo({
  posicao,
  aceso,
  emChoque,
  doCrime,
  naHoraDoCrime,
  aoClicar,
}: {
  posicao: [number, number]
  aceso: boolean
  emChoque: boolean
  doCrime: boolean
  naHoraDoCrime: boolean
  aoClicar: () => void
}) {
  const [sobre, setSobre] = useState(false)
  const meio = LADO / 2 - PAREDE_ESPESSURA / 2

  // O choque tinge a parede, não o chão inteiro: preencher o cômodo de laranja
  // gritava mais que o achado merecia e apagava tudo que estava em cima dele.
  const corParede = emChoque ? ALARME : aceso || sobre ? PAREDE_ALTA : PAREDE

  return (
    <group
      position={[posicao[0], 0, posicao[1]]}
      onClick={(evento: ThreeEvent<MouseEvent>) => {
        evento.stopPropagation()
        aoClicar()
      }}
      onPointerOver={() => setSobre(true)}
      onPointerOut={() => setSobre(false)}
    >
      <mesh receiveShadow>
        <boxGeometry args={[LADO, 0.22, LADO]} />
        <meshLambertMaterial color={aceso || sobre ? PISO_ALVO : PISO} />
      </mesh>

      {/* Quatro paredes baixas. É o que separa "azulejo flutuando" de cômodo. */}
      {(
        [
          [0, -meio, LADO, PAREDE_ESPESSURA],
          [0, meio, LADO, PAREDE_ESPESSURA],
          [-meio, 0, PAREDE_ESPESSURA, LADO],
          [meio, 0, PAREDE_ESPESSURA, LADO],
        ] as const
      ).map(([x, z, largura, fundo], i) => (
        <mesh key={i} position={[x, PAREDE_ALTURA / 2 + 0.11, z]} castShadow>
          <boxGeometry args={[largura, PAREDE_ALTURA, fundo]} />
          <meshLambertMaterial color={corParede} />
        </mesh>
      ))}

      {/* Onde o corpo foi encontrado. O briefing já diz em prosa; aqui é a
          mesma coisa dita de um jeito que não exige reler a frase. */}
      {doCrime ? (
        <mesh position={[0, 0.13, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.52, 0.68, 4, 1, Math.PI / 4]} />
          <meshBasicMaterial
            color={OSSO}
            transparent
            opacity={naHoraDoCrime ? 0.95 : 0.3}
            side={THREE.DoubleSide}
          />
        </mesh>
      ) : null}
    </group>
  )
}

/** Carrega o retrato como textura. Sem retrato, a peça fica sem face. */
function useRetratoTextura(nome: string): THREE.Texture | null {
  const [textura, setTextura] = useState<THREE.Texture | null>(null)
  const url = retratoDe(nome)

  useEffect(() => {
    if (!url) return
    let vivo = true
    const carregador = new THREE.TextureLoader()
    carregador.load(url, (t) => {
      if (!vivo) return
      t.colorSpace = THREE.SRGBColorSpace
      setTextura(t)
    })
    return () => {
      vivo = false
    }
  }, [url])

  useEffect(() => () => textura?.dispose(), [textura])
  return textura
}

/**
 * Um suspeito onde o jogador o colocou — de pé, com a cara dele.
 *
 * O cilindro com iniciais não servia: duas pessoas podem ter as mesmas letras,
 * e um disco visto de cima esconde justamente o que identifica alguém. A carta
 * fica em pé, virada para a câmera, e como a câmera não se move ela não precisa
 * ser reorientada a cada quadro.
 */
function PecaNaPlanta({
  posicao,
  nome,
  destacado,
  escala,
}: {
  posicao: [number, number]
  nome: string
  destacado: boolean
  escala: number
}) {
  const textura = useRetratoTextura(nome)
  const carta = useRef<THREE.Group>(null)
  const { camera } = useThree()

  useEffect(() => {
    carta.current?.lookAt(camera.position)
  }, [camera])

  const largura = 0.78 * escala
  const altura = largura * 1.28

  return (
    <group position={[posicao[0], 0.12, posicao[1]]} scale={escala}>
      <mesh position={[0, 0.02, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[0.34, 20]} />
        <meshBasicMaterial color={destacado ? OSSO : '#575263'} />
      </mesh>
      <group ref={carta} position={[0, altura / 2 + 0.06, 0]}>
        <mesh position={[0, 0, -0.01]}>
          <planeGeometry args={[largura + 0.07, altura + 0.07]} />
          <meshBasicMaterial color={destacado ? OSSO : '#3a3d4d'} />
        </mesh>
        {textura ? (
          <mesh>
            <planeGeometry args={[largura, altura]} />
            <meshBasicMaterial map={textura} toneMapped={false} />
          </mesh>
        ) : null}
      </group>
    </group>
  )
}

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
      // Na quina da frente, fora do ladrilho: em cima do cômodo o rótulo
      // atravessava as peças e ficava ilegível.
      const v = new THREE.Vector3(x, 0, z + LADO / 2 + VAO * 0.45).project(camera)
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
  pecas: Peca[]
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

  const porComodo = useMemo(() => {
    const mapa = new Map<string, Peca[]>()
    for (const peca of pecas) {
      const lista = mapa.get(peca.comodo) ?? []
      lista.push(peca)
      mapa.set(peca.comodo, lista)
    }
    return mapa
  }, [pecas])

  const naHoraDoCrime = hora === plan.crime_interval

  return (
    <div className={styles.palco}>
      <Canvas
        orthographic
        shadows
        camera={{ position: [9, 9, 9], zoom: 58, near: -50, far: 100 }}
        style={{ background: NOITE }}
      >
        <ambientLight intensity={1.05} />
        {/* Uma luz só, vinda de onde vem a luz nos retratos: da esquerda. */}
        <directionalLight position={[-6, 10, 4]} intensity={2.1} castShadow />

        {[...assento].map(([id, posicao]) => (
          <Comodo
            key={id}
            posicao={posicao}
            aceso={selecionado === id}
            emChoque={emChoque.has(id)}
            doCrime={id === plan.crime_room}
            naHoraDoCrime={naHoraDoCrime}
            aoClicar={() => aoEscolherComodo(id)}
          />
        ))}

        {[...porComodo].map(([comodo, lista]) => {
          const base = assento.get(comodo)
          if (!base) return null
          const { grade, escala } = arrumar(lista.length)
          const passo = (LADO - 0.5) / grade
          return lista.map((peca, i) => {
            const coluna = i % grade
            const linha = Math.floor(i / grade)
            return (
              <PecaNaPlanta
                key={`${comodo}-${peca.suspeito}`}
                posicao={[
                  base[0] + (coluna - (grade - 1) / 2) * passo,
                  base[1] + (linha - (grade - 1) / 2) * passo,
                ]}
                nome={peca.nome}
                destacado={peca.destacado}
                escala={escala}
              />
            )
          })
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
          className={[
            styles.rotulo,
            emChoque.has(rotulo.id) ? styles.rotuloChoque : '',
            rotulo.id === plan.crime_room ? styles.rotuloCrime : '',
          ]
            .filter(Boolean)
            .join(' ')}
          style={{ left: rotulo.x, top: rotulo.y }}
        >
          {rotulo.nome}
        </span>
      ))}
    </div>
  )
}
