'use client'

/**
 * Como cada móvel se parece.
 *
 * Dez espécies vêm de modelos do **Quaternius** (CC0), e duas continuam sendo
 * primitivas porque o pacote não as tem: barril e caixote. Ver
 * `public/moveis/PROVENIENCIA.md`.
 *
 * ## Os modelos são normalizados, não usados como vieram
 *
 * Cada um chega com a própria escala, o próprio centro e a própria altura de
 * chão. Encaixá-los à mão seria dez números mágicos que quebram no primeiro
 * modelo trocado — então a caixa envolvente é medida no carregamento e o móvel
 * é escalado até caber no vulto que `mobilia.ts` reserva para a espécie,
 * assentado com a base no chão e centrado no lugar.
 *
 * É isso que mantém a promessa de que nada atravessa parede: o vulto é a
 * mesma medida que a conferência usa.
 */

import { useEffect, useMemo, useState } from 'react'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'

import { moveisDe, VULTO, type Especie, type Movel } from '@/lib/mobilia'

const MADEIRA = '#6d5c46'
const MADEIRA_CLARA = '#7f6d53'
const MADEIRA_ESCURA = '#54462f'
const FERRO = '#3b3a38'

/** Espécie que tem modelo, e o arquivo dela. */
const MODELO: Partial<Record<Especie, string>> = {
  mesa: 'mesa',
  cadeira: 'cadeira',
  estante: 'estante',
  poltrona: 'poltrona',
  vaso: 'vaso',
  bancada: 'bancada',
  fogao: 'fogao',
  escrivaninha: 'comoda',
  lareira: 'lareira',
}

// Um carregamento por arquivo, por mais instâncias que existam na casa.
const carregados = new Map<string, Promise<THREE.Object3D>>()

function buscar(arquivo: string): Promise<THREE.Object3D> {
  let promessa = carregados.get(arquivo)
  if (!promessa) {
    promessa = new GLTFLoader()
      .loadAsync(`/moveis/${arquivo}.glb`)
      .then((gltf) => gltf.scene)
    carregados.set(arquivo, promessa)
  }
  return promessa
}

/**
 * O modelo, escalado e assentado dentro do vulto da espécie.
 *
 * A largura manda: encolher pela maior dimensão deixaria a estante anã ao lado
 * da mesa, porque uma é alta e a outra é comprida.
 */
function useModelo(especie: Especie, alvo: {
  largura: number
  altura: number
  fundo: number
}): THREE.Object3D | null {
  const arquivo = MODELO[especie]
  const [pronto, setPronto] = useState<THREE.Object3D | null>(null)

  useEffect(() => {
    if (!arquivo) return
    let vivo = true
    buscar(arquivo).then((cena) => {
      if (!vivo) return
      const copia = cena.clone(true)
      const caixa = new THREE.Box3().setFromObject(copia)
      const tamanho = caixa.getSize(new THREE.Vector3())
      const centro = caixa.getCenter(new THREE.Vector3())

      const fator = Math.min(
        alvo.largura / (tamanho.x || 1),
        alvo.altura / (tamanho.y || 1),
        alvo.fundo / (tamanho.z || 1),
      )
      copia.scale.setScalar(fator)
      // Base no chão, centrado em x e z.
      copia.position.set(
        -centro.x * fator,
        -caixa.min.y * fator,
        -centro.z * fator,
      )
      copia.traverse((no) => {
        if ((no as THREE.Mesh).isMesh) {
          no.castShadow = true
          no.receiveShadow = true
        }
      })
      setPronto(copia)
    })
    return () => {
      vivo = false
    }
  }, [arquivo, alvo.largura, alvo.altura, alvo.fundo])

  return pronto
}

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

/** Barril: o pacote do Quaternius não tem, e uma adega sem barril não é adega. */
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

/** Caixote, pelo mesmo motivo. As ripas é que impedem de virar cubo. */
function Caixote({ l, a, f }: { l: number; a: number; f: number }) {
  return (
    <>
      <Tabua em={[0, a / 2, 0]} tamanho={[l, a, f]} cor={MADEIRA_ESCURA} />
      <Tabua
        em={[0, a * 0.28, 0]}
        tamanho={[l + 0.01, 0.035, f + 0.01]}
        cor={MADEIRA_CLARA}
      />
      <Tabua
        em={[0, a * 0.78, 0]}
        tamanho={[l + 0.01, 0.035, f + 0.01]}
        cor={MADEIRA_CLARA}
      />
    </>
  )
}

function Movelzinho({ movel, lado }: { movel: Movel; lado: number }) {
  const vulto = VULTO[movel.especie]
  const escala = movel.escala ?? 1
  const alvo = useMemo(
    () => ({
      largura: vulto.largura * lado * escala,
      altura: vulto.altura * lado * escala,
      fundo: vulto.fundo * lado * escala,
    }),
    [vulto, lado, escala],
  )
  const modelo = useModelo(movel.especie, alvo)

  return (
    <group
      position={[movel.em[0] * lado, 0.11, movel.em[1] * lado]}
      rotation={[0, ((movel.giro ?? 0) * Math.PI) / 2, 0]}
    >
      {modelo ? (
        <primitive object={modelo} />
      ) : movel.especie === 'barril' ? (
        <Barril l={alvo.largura} a={alvo.altura} />
      ) : movel.especie === 'caixote' ? (
        <Caixote l={alvo.largura} a={alvo.altura} f={alvo.fundo} />
      ) : null}
    </group>
  )
}

export default function Moveis({
  comodo,
  lado,
}: {
  comodo: string
  lado: number
}) {
  const moveis = useMemo(() => moveisDe(comodo), [comodo])
  return (
    <>
      {moveis.map((movel, i) => (
        <Movelzinho key={i} movel={movel} lado={lado} />
      ))}
    </>
  )
}
