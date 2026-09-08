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
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'

import type { FloorPlan } from '@/lib/api'
import { silhuetaDeGiz } from '@/lib/giz'
import { degrauDe, lugarLivre } from '@/lib/mobilia'
import { retratoDe } from '@/lib/retratos'

import Moveis from './Moveis'
import styles from './Planta.module.css'

const NOITE = '#14161f'
const PISO = '#262a38'
// Chega menos luz numa adega, e a cor diz isso antes da geometria.
const PISO_FUNDO = '#1b1e29'
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
const DEGRAU_ALTURA = 0.6
// Quanto do cômodo a silhueta de giz ocupa, e quanto dela precisa de chão
// limpo. São dois números porque o desenho é um corpo esparramado: o tronco
// tem que cair em piso vago, mas um braço passando por baixo de uma cadeira é
// como um corpo cai de verdade. Procurar espaço para o quadro inteiro não
// achava lugar nenhum na sala de jantar.
const GIZ = 0.38
const GIZ_NUCLEO = 0.22
// Um pouco torta: giz no chão não sai alinhado com a parede, e alinhada ela
// parecia mais um ícone colado que uma marca feita ali.
const GIRO_DO_GIZ = 0.55

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
  comodo,
  posicao,
  aceso,
  emChoque,
  doCrime,
  naHoraDoCrime,
  giz,
  aoClicar,
}: {
  comodo: string
  posicao: [number, number]
  aceso: boolean
  emChoque: boolean
  doCrime: boolean
  naHoraDoCrime: boolean
  giz: THREE.Texture | null
  aoClicar: () => void
}) {
  const [sobre, setSobre] = useState(false)
  const meio = LADO / 2 - PAREDE_ESPESSURA / 2
  const vago = useMemo<[number, number]>(
    () => lugarLivre(comodo, GIZ_NUCLEO, GIZ_NUCLEO) ?? [0, 0],
    [comodo],
  )
  const degrau = degrauDe(comodo)
  const afundado = degrau < 0
  const fundura = Math.abs(degrau) * DEGRAU_ALTURA

  // O choque tinge a parede, não o chão inteiro: preencher o cômodo de laranja
  // gritava mais que o achado merecia e apagava tudo que estava em cima dele.
  const corParede = emChoque ? ALARME : aceso || sobre ? PAREDE_ALTA : PAREDE

  return (
    <group
      position={[posicao[0], degrauDe(comodo) * DEGRAU_ALTURA, posicao[1]]}
      onClick={(evento: ThreeEvent<MouseEvent>) => {
        evento.stopPropagation()
        aoClicar()
      }}
      onPointerOver={() => setSobre(true)}
      onPointerOut={() => setSobre(false)}
    >
      {/* Em isométrico, descer no eixo Y é indistinguível de andar para o sul
          na grade — foi por isso que o degrau não aparecia. Quem diz
          "profundidade" é a face lateral: o cômodo afundado ganha uma laje que
          sobe até o nível do térreo, e é essa parede alta que se vê. */}
      <mesh position={[0, -fundura / 2, 0]} receiveShadow castShadow>
        <boxGeometry args={[LADO, 0.22 + fundura, LADO]} />
        <meshLambertMaterial
          color={aceso || sobre ? PISO_ALVO : afundado ? PISO_FUNDO : PISO}
        />
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

      <Moveis comodo={comodo} lado={LADO} />

      {/* Onde o corpo foi encontrado. Era um losango branco, que diz "aqui" e
          nada mais; a silhueta de giz diz a mesma coisa e ainda diz o quê.
          Fica num ponto do cômodo que a mobília deixou vago — no centro ela
          caía dentro da mesa de jantar. */}
      {doCrime && giz ? (
        <mesh
          position={[vago[0] * LADO, 0.125, vago[1] * LADO]}
          rotation={[-Math.PI / 2, 0, GIRO_DO_GIZ]}
        >
          <planeGeometry args={[GIZ * LADO, GIZ * LADO]} />
          <meshBasicMaterial
            map={giz}
            transparent
            depthWrite={false}
            opacity={naHoraDoCrime ? 1 : 0.42}
            side={THREE.DoubleSide}
          />
        </mesh>
      ) : null}
    </group>
  )
}

/**
 * A silhueta de giz como textura, desenhada no navegador.
 *
 * Num efeito e não durante a renderização porque canvas não existe no
 * servidor, e esta árvore é renderizada lá antes de chegar ao navegador.
 */
function useGiz(): THREE.Texture | null {
  // Sem descarte na desmontagem de propósito: em modo estrito o React monta,
  // limpa e monta de novo, e a limpeza liberaria uma textura que a segunda
  // montagem ainda usa. Ela vive tanto quanto o canvas, e vai embora com ele.
  return useMemo(() => {
    if (typeof document === 'undefined') return null
    const desenhada = new THREE.CanvasTexture(silhuetaDeGiz(OSSO))
    desenhada.colorSpace = THREE.SRGBColorSpace
    return desenhada
  }, [])
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
  andar,
  nome,
  destacado,
  escala,
}: {
  posicao: [number, number]
  andar: number
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
    <group position={[posicao[0], andar + 0.12, posicao[1]]} scale={escala}>
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

/** Onde cada cômodo caiu na tela: o ponto do rótulo e o ladrilho inteiro. */
type Medida = {
  id: string
  nome: string
  x: number
  y: number
  /** Os quatro cantos do chão, em pixels do palco. É o alvo de quem arrasta. */
  quadro: [number, number][]
}

/**
 * Projeta os cômodos para coordenadas de tela, uma vez por tamanho de canvas.
 *
 * A câmera é fixa, então isto não precisa acontecer a cada quadro — mas
 * precisa acontecer de novo quando o palco muda de tamanho, senão o rótulo
 * fica torto e, pior, largar um retrato acerta o cômodo errado.
 */
function Medir({
  assento,
  nomes,
  aoMedir,
}: {
  assento: Map<string, [number, number]>
  nomes: Map<string, string>
  aoMedir: (medidas: Medida[]) => void
}) {
  const { camera, size } = useThree()

  useEffect(() => {
    const emTela = (x: number, y: number, z: number): [number, number] => {
      const v = new THREE.Vector3(x, y, z).project(camera)
      return [((v.x + 1) / 2) * size.width, ((1 - v.y) / 2) * size.height]
    }

    const medidas = [...assento].map(([id, [x, z]]) => {
      const andar = degrauDe(id) * DEGRAU_ALTURA
      const meio = LADO / 2
      // Na quina da frente, fora do ladrilho: em cima do cômodo o rótulo
      // atravessava as peças e ficava ilegível.
      const [rx, ry] = emTela(x, andar, z + LADO / 2 + VAO * 0.45)
      return {
        id,
        nome: nomes.get(id) ?? id,
        x: rx,
        y: ry,
        quadro: [
          emTela(x - meio, andar, z - meio),
          emTela(x + meio, andar, z - meio),
          emTela(x + meio, andar, z + meio),
          emTela(x - meio, andar, z + meio),
        ] as [number, number][],
      }
    })
    aoMedir(medidas)
  }, [assento, nomes, camera, size, aoMedir])

  return null
}

/** Ponto dentro do quadrilátero convexo: mesmo lado de todas as arestas. */
function dentro(ponto: [number, number], quadro: [number, number][]): boolean {
  let sinal = 0
  for (let i = 0; i < quadro.length; i++) {
    const a = quadro[i]!
    const b = quadro[(i + 1) % quadro.length]!
    const cruz = (b[0] - a[0]) * (ponto[1] - a[1]) - (b[1] - a[1]) * (ponto[0] - a[0])
    if (cruz === 0) continue
    const lado = cruz > 0 ? 1 : -1
    if (sinal === 0) sinal = lado
    else if (sinal !== lado) return false
  }
  return true
}

export default function Planta({
  plan,
  hora,
  pecas,
  emChoque,
  selecionado,
  preencher = false,
  aoEscolherComodo,
  aoSoltarSuspeito,
}: {
  plan: FloorPlan
  hora: number
  pecas: Peca[]
  emChoque: Set<string>
  selecionado: string | null
  /** Ocupa a altura que sobrar em vez de guardar a proporção 4:3. */
  preencher?: boolean
  aoEscolherComodo: (comodo: string) => void
  /** Alguém foi largado num cômodo. Sem isto a planta não aceita arrasto. */
  aoSoltarSuspeito?: (comodo: string, suspeito: string) => void
}) {
  const comodos = useMemo(() => plan.rooms.map((r) => r.id), [plan])
  const assento = useMemo(() => assentar(comodos), [comodos])
  const nomes = useMemo(
    () => new Map(plan.rooms.map((r) => [r.id, r.name])),
    [plan],
  )
  const [medidas, setMedidas] = useState<Medida[]>([])
  // Identidade estável: o efeito que mede depende dela, e uma função nova a
  // cada render faria a medida rodar em laço.
  const guardarMedidas = useCallback((novas: Medida[]) => setMedidas(novas), [])
  const palco = useRef<HTMLDivElement>(null)
  const [alvo, setAlvo] = useState<string | null>(null)

  /** Em que cômodo o ponteiro está, na hora de largar alguém. */
  const comodoSob = useCallback(
    (evento: { clientX: number; clientY: number }): string | null => {
      const caixa = palco.current?.getBoundingClientRect()
      if (!caixa) return null
      const ponto: [number, number] = [
        evento.clientX - caixa.left,
        evento.clientY - caixa.top,
      ]
      // De trás para a frente: os cômodos da frente desenham por cima, então
      // ganham o empate onde os ladrilhos se encostam.
      for (let i = medidas.length - 1; i >= 0; i--) {
        const medida = medidas[i]!
        if (dentro(ponto, medida.quadro)) return medida.id
      }
      return null
    },
    [medidas],
  )

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
  const giz = useGiz()

  return (
    <div
      ref={palco}
      className={preencher ? styles.palcoCheio : styles.palco}
      onDragOver={
        aoSoltarSuspeito
          ? (evento) => {
              // Sem o preventDefault o navegador recusa o alvo e não há solta.
              evento.preventDefault()
              evento.dataTransfer.dropEffect = 'move'
              setAlvo(comodoSob(evento))
            }
          : undefined
      }
      onDragLeave={aoSoltarSuspeito ? () => setAlvo(null) : undefined}
      onDrop={
        aoSoltarSuspeito
          ? (evento) => {
              evento.preventDefault()
              const quem = evento.dataTransfer.getData('text/plain')
              const comodo = comodoSob(evento)
              setAlvo(null)
              if (quem && comodo) aoSoltarSuspeito(comodo, quem)
            }
          : undefined
      }
    >
      {/* `shadows` sozinho pede PCFSoftShadowMap, que o three 185 depreciou —
          e o aviso sai *por quadro*, não uma vez. Pior: o r3f reaplica o tipo
          a cada render, então cada render devolve o aviso à vida. Arrastar um
          retrato dispara dezenas de renders por segundo, o console inunda e a
          aba trava. `percentage` é o mesmo algoritmo sem a versão aposentada. */}
      <Canvas
        orthographic
        shadows="percentage"
        camera={{ position: [9, 9, 9], zoom: 58, near: -50, far: 100 }}
        style={{ background: NOITE }}
      >
        <ambientLight intensity={1.05} />
        {/* Uma luz só, vinda de onde vem a luz nos retratos: da esquerda. */}
        <directionalLight position={[-6, 10, 4]} intensity={2.1} castShadow />

        {[...assento].map(([id, posicao]) => (
          <Comodo
            key={id}
            comodo={id}
            posicao={posicao}
            aceso={selecionado === id || alvo === id}
            emChoque={emChoque.has(id)}
            doCrime={id === plan.crime_room}
            naHoraDoCrime={naHoraDoCrime}
            giz={giz}
            aoClicar={() => aoEscolherComodo(id)}
          />
        ))}

        {[...porComodo].map(([comodo, lista]) => {
          const base = assento.get(comodo)
          if (!base) return null
          const { grade, escala } = arrumar(lista.length)
          const passo = (LADO - 0.6) / grade
          // Gente na frente, mobília no fundo. Sem isso a primeira peça de um
          // cômodo nasce dentro da mesa, e o retrato — que é o que identifica
          // alguém — fica atrás do móvel.
          // Encolhe junto com a grade: com muita gente nao sobra frente para
          // onde empurrar, e o que importa e nao estourar a parede.
          const frente = (LADO * 0.2) / grade
          return lista.map((peca, i) => {
            const coluna = i % grade
            const linha = Math.floor(i / grade)
            return (
              <PecaNaPlanta
                key={`${comodo}-${peca.suspeito}`}
                posicao={[
                  base[0] + (coluna - (grade - 1) / 2) * passo,
                  base[1] + frente + (linha - (grade - 1) / 2) * passo,
                ]}
                andar={degrauDe(comodo) * DEGRAU_ALTURA}
                nome={peca.nome}
                destacado={peca.destacado}
                escala={escala}
              />
            )
          })
        })}

        <Medir assento={assento} nomes={nomes} aoMedir={guardarMedidas} />
      </Canvas>

      {medidas.map((rotulo) => (
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
