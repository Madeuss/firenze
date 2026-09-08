'use client'

/**
 * Modo Dedução: a planta, a linha do tempo e a grade de quem esteve onde.
 *
 * **Não gasta turno, e isso é metade do design.** O jogador precisa sentir que
 * pode raciocinar sem estar sendo cobrado — perguntar custa, pensar não
 * (docs/03-casos-de-uso.md §2).
 *
 * A planta chega vazia e quem a preenche é ele. Escolhe uma célula da grade,
 * clica num cômodo, e a peça aparece lá quando a linha do tempo passa por
 * aquela hora. Dois no mesmo cômodo na mesma hora acendem — o jogo não impede,
 * porque o choque é justamente o achado.
 *
 * `vista` diz qual metade mostrar. Numa tela larga as duas viram abas do painel
 * ao lado da conversa, e o componente continua sendo um só de propósito: a hora
 * escolhida e a célula em aberto são estado daqui, então trocar de aba não
 * perde o que o jogador estava fazendo.
 */

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
  type CSSProperties,
} from 'react'

import type { CastMember, MatchState } from '@/lib/api'
import { useTextos } from '@/lib/idioma'
import { com } from '@/lib/textos'
import {
  anotar,
  assinar,
  choques,
  escrever,
  instantaneo,
  instantaneoDoServidor,
  onde,
} from '@/lib/notas'

import { Skull } from 'lucide-react'

import EscolherComodo from './EscolherComodo'
import Planta, { type Bussola, type Peca } from './Planta'
import Retrato from './Retrato'
import styles from './Deducao.module.css'

export type Vista = 'planta' | 'grade' | 'ambos'

export default function Deducao({
  match,
  vista = 'ambos',
}: {
  match: MatchState
  vista?: Vista
}) {
  const t = useTextos()
  const notas = useSyncExternalStore(
    assinar,
    () => instantaneo(match.id),
    instantaneoDoServidor,
  )
  const [hora, setHora] = useState(0)
  const [celula, setCelula] = useState<{
    suspeito: string
    hora: number
  } | null>(null)
  // Quem está na mão: pego na bandeja ou tirado de um cômodo. Um estado só
  // para os dois porque, para o jogador, é o mesmo gesto.
  const [naMao, setNaMao] = useState<{
    quem: string
    de: string | null
  } | null>(null)
  const [alvo, setAlvo] = useState<string | null>(null)
  // O gesto em curso mora numa ref, não no estado: ele muda a cada pixel do
  // ponteiro, e um estado por pixel re-renderizaria a cena 3D inteira.
  const gesto = useRef<{ x0: number; y0: number; andou: boolean } | null>(null)
  const bussola = useRef<Bussola | null>(null)
  const fantasma = useRef<HTMLDivElement>(null)

  const suspeitos = useMemo(
    () => match.cast.filter((p): p is CastMember => p.role === 'suspect'),
    [match],
  )
  const emChoque = useMemo(() => choques(notas, hora), [notas, hora])

  const registrar = useCallback(
    (suspeito: string, quando: number, comodo: string | null) => {
      escrever(
        match.id,
        anotar(instantaneo(match.id), suspeito, quando, comodo),
      )
    },
    [match.id],
  )

  const escolherComodo = useCallback(
    (comodo: string) => {
      if (naMao) {
        registrar(naMao.quem, hora, comodo)
        setNaMao(null)
        return
      }
      if (!celula) return
      const jaEsta = onde(notas, celula.suspeito, celula.hora) === comodo
      registrar(celula.suspeito, celula.hora, jaEsta ? null : comodo)
      setCelula(null)
    },
    [celula, hora, naMao, notas, registrar],
  )

  const fecharCelula = useCallback(() => setCelula(null), [])

  /** Pegar alguém: da bandeja (`de` vazio) ou de dentro de um cômodo. */
  const pegar = useCallback(
    (
      quem: string,
      de: string | null,
      evento: { clientX: number; clientY: number },
    ) => {
      gesto.current = { x0: evento.clientX, y0: evento.clientY, andou: false }
      setNaMao({ quem, de })
      setAlvo(de)
    },
    [],
  )

  /**
   * O gesto, enquanto dura.
   *
   * Três desfechos ao soltar: em cima de um cômodo, a pessoa fica lá; fora da
   * planta, quem veio de um cômodo volta para a bandeja; e se o ponteiro não
   * andou, não foi arrasto e sim clique — a pessoa continua na mão, para ser
   * colocada com um segundo clique. É esse terceiro caminho que faz o modo
   * funcionar no toque, onde arrastar de um canvas é sofrimento.
   */
  useEffect(() => {
    if (!naMao) return
    const carregado = naMao

    function mover(evento: PointerEvent) {
      const atual = gesto.current
      if (atual && !atual.andou) {
        atual.andou =
          Math.abs(evento.clientX - atual.x0) > 4 ||
          Math.abs(evento.clientY - atual.y0) > 4
      }
      if (fantasma.current) {
        fantasma.current.style.transform = `translate(${evento.clientX}px, ${evento.clientY}px)`
      }
      // Vira estado só quando muda de cômodo: um estado por pixel refaria a
      // cena 3D inteira a cada movimento do ponteiro.
      setAlvo(bussola.current?.comodoSob(evento) ?? null)
    }

    function soltar(evento: PointerEvent) {
      const atual = gesto.current
      gesto.current = null
      if (!atual?.andou) return

      const comodo = bussola.current?.comodoSob(evento) ?? null
      if (comodo) registrar(carregado.quem, hora, comodo)
      else if (carregado.de) registrar(carregado.quem, hora, null)
      setNaMao(null)
      setAlvo(null)
    }

    window.addEventListener('pointermove', mover)
    window.addEventListener('pointerup', soltar)
    return () => {
      window.removeEventListener('pointermove', mover)
      window.removeEventListener('pointerup', soltar)
    }
  }, [naMao, hora, registrar])

  // A bandeja é o avesso da planta: quem não está em cômodo nenhum nesta hora.
  // Mudar de hora esvazia a planta e devolve todo mundo para cá, que é o que
  // torna a linha do tempo uma linha do tempo e não um desenho só.
  const naBandeja = useMemo(
    () => suspeitos.filter((pessoa) => !onde(notas, pessoa.id, hora)),
    [suspeitos, notas, hora],
  )

  const pecas = useMemo<Peca[]>(
    () =>
      suspeitos
        .map((pessoa) => ({ pessoa, comodo: onde(notas, pessoa.id, hora) }))
        .filter((p): p is { pessoa: CastMember; comodo: string } => !!p.comodo)
        .map(({ pessoa, comodo }) => ({
          suspeito: pessoa.id,
          nome: pessoa.name,
          comodo,
          destacado: celula?.suspeito === pessoa.id,
        })),
    [suspeitos, notas, hora, celula],
  )

  const nomeDoComodo = useMemo(
    () => new Map(match.plan.rooms.map((c) => [c.id, c.name])),
    [match.plan],
  )

  const planta = (
    <div className={styles.coluna}>
      <div className={styles.tabuleiro}>
        <Planta
          preencher={vista === 'planta'}
          plan={match.plan}
          hora={hora}
          pecas={pecas}
          emChoque={emChoque}
          selecionado={
            celula ? onde(notas, celula.suspeito, celula.hora) : null
          }
          aoEscolherComodo={escolherComodo}
          alvo={alvo}
          aoPegarPeca={(quem, de, evento) => pegar(quem, de, evento)}
          bussola={bussola}
        />

        {/* Quem ainda não tem lugar nesta hora. Arraste para um cômodo — ou,
              se arrastar não der, clique no retrato e depois no cômodo. */}
        <div
          className={styles.bandeja}
          aria-label={t['deducao.bandeja']}
        >
          {naBandeja.map((pessoa) => (
            <button
              key={pessoa.id}
              className={
                naMao?.quem === pessoa.id ? styles.fichaNaMao : styles.ficha
              }
              onPointerDown={(evento) => {
                if (naMao?.quem === pessoa.id) {
                  setNaMao(null)
                  setAlvo(null)
                  return
                }
                pegar(pessoa.id, null, evento.nativeEvent)
              }}
              title={com(t['deducao.onde'], { nome: pessoa.name })}
            >
              <Retrato
                nome={pessoa.name}
                tamanho={38}
                aceso={naMao?.quem === pessoa.id}
              />
              <span className={styles.fichaNome}>
                {pessoa.name.split(' ')[0]}
              </span>
            </button>
          ))}
          {naBandeja.length === 0 ? (
            <span className={styles.bandejaVazia}>
              {t['deducao.bandeja.vazia']}
            </span>
          ) : null}
        </div>
      </div>

      <div className={styles.relogio}>
        {/* A hora da morte marcada no trilho, na mesma cruz que marca o
              cômodo na planta. Sem ela o jogador tinha que guardar de cabeça
              qual intervalo importava enquanto arrastava. */}
        <div className={styles.trilho}>
          <span
            className={styles.marcaCrime}
            style={
              {
                '--fracao': String(
                  match.plan.hours.length > 1
                    ? match.plan.crime_interval / (match.plan.hours.length - 1)
                    : 0,
                ),
              } as CSSProperties
            }
            title={t['deducao.hora.crime']}
          >
            <Skull size={19} strokeWidth={2} />
          </span>
          <input
            type="range"
            min={0}
            max={match.plan.hours.length - 1}
            value={hora}
            onChange={(e) => setHora(Number(e.target.value))}
            aria-label={t['deducao.hora']}
          />
        </div>
        <div className={styles.horas}>
          {match.plan.hours.map((h) => (
            <button
              key={h.interval}
              className={[
                h.interval === hora ? styles.horaAgora : styles.hora,
                h.interval === match.plan.crime_interval
                  ? styles.horaCrime
                  : '',
              ]
                .filter(Boolean)
                .join(' ')}
              onClick={() => setHora(h.interval)}
            >
              {h.label}
              {h.interval === match.plan.crime_interval ? (
                <Skull size={11} strokeWidth={1.75} />
              ) : null}
            </button>
          ))}
        </div>
      </div>
    </div>
  )

  const grade = (
    <div className={styles.coluna}>
      <p className={styles.instrucao}>
        {naMao
          ? com(t['deducao.solte'], {
              nome:
                match.cast.find((p) => p.id === naMao.quem)?.name ?? naMao.quem,
            })
          : t['deducao.instrucao']}
      </p>

      <table className={styles.grade}>
        <thead>
          <tr>
            <th />
            {match.plan.hours.map((h) => (
              <th key={h.interval}>{h.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {suspeitos.map((pessoa) => (
            <tr key={pessoa.id}>
              <th scope="row">
                {pessoa.name}
                {/* A grade é lida de relance. A função é o que faz "quem é
                      esse" caber numa linha da tabela. */}
                {pessoa.occupation ? (
                  <span className={styles.funcao}>{pessoa.occupation}</span>
                ) : null}
              </th>
              {match.plan.hours.map((h) => {
                const comodo = onde(notas, pessoa.id, h.interval)
                const escolhida =
                  celula?.suspeito === pessoa.id && celula.hora === h.interval
                const bate = !!comodo && choques(notas, h.interval).has(comodo)
                return (
                  <td key={h.interval} className={styles.gaveta}>
                    <button
                      className={[
                        styles.celula,
                        escolhida ? styles.celulaEscolhida : '',
                        bate ? styles.celulaChoque : '',
                      ]
                        .filter(Boolean)
                        .join(' ')}
                      onClick={() =>
                        setCelula(
                          escolhida
                            ? null
                            : { suspeito: pessoa.id, hora: h.interval },
                        )
                      }
                      title={
                        comodo ? nomeDoComodo.get(comodo) : t['deducao.celula.vazia']
                      }
                    >
                      {comodo ? nomeDoComodo.get(comodo)?.slice(0, 3) : '·'}
                    </button>

                    {escolhida ? (
                      <EscolherComodo
                        comodos={match.plan.rooms}
                        atual={comodo}
                        aoEscolher={(escolhido) => {
                          registrar(pessoa.id, h.interval, escolhido)
                          setCelula(null)
                        }}
                        aoFechar={fecharCelula}
                      />
                    ) : null}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )

  return (
    <div className={vista === 'ambos' ? styles.mesa : styles.sozinha}>
      {vista === 'grade' ? null : planta}
      {vista === 'planta' ? null : grade}

      {/* Quem está na mão acompanha o ponteiro. Posicionado direto no elemento,
          sem passar pelo estado do React: são dezenas de posições por segundo,
          e cada uma custaria um render da cena inteira. */}
      {naMao ? (
        <div ref={fantasma} className={styles.fantasma}>
          <Retrato
            nome={
              match.cast.find((p) => p.id === naMao.quem)?.name ?? naMao.quem
            }
            tamanho={44}
          />
        </div>
      ) : null}
    </div>
  )
}
