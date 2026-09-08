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
  useMemo,
  useState,
  useSyncExternalStore,
  type CSSProperties,
} from 'react'

import type { CastMember, MatchState } from '@/lib/api'
import {
  anotar,
  assinar,
  choques,
  escrever,
  instantaneo,
  instantaneoDoServidor,
  onde,
} from '@/lib/notas'

import Planta, { type Peca } from './Planta'
import styles from './Deducao.module.css'

export type Vista = 'planta' | 'grade' | 'ambos'

export default function Deducao({
  match,
  vista = 'ambos',
}: {
  match: MatchState
  vista?: Vista
}) {
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

  const suspeitos = useMemo(
    () => match.cast.filter((p): p is CastMember => p.role === 'suspect'),
    [match],
  )
  const emChoque = useMemo(() => choques(notas, hora), [notas, hora])

  const registrar = useCallback(
    (suspeito: string, quando: number, comodo: string | null) => {
      escrever(match.id, anotar(instantaneo(match.id), suspeito, quando, comodo))
    },
    [match.id],
  )

  const escolherComodo = useCallback(
    (comodo: string) => {
      if (!celula) return
      const jaEsta = onde(notas, celula.suspeito, celula.hora) === comodo
      registrar(celula.suspeito, celula.hora, jaEsta ? null : comodo)
      setCelula(null)
    },
    [celula, notas, registrar],
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
        <Planta
          preencher={vista === 'planta'}
          plan={match.plan}
          hora={hora}
          pecas={pecas}
          emChoque={emChoque}
          selecionado={celula ? onde(notas, celula.suspeito, celula.hora) : null}
          aoEscolherComodo={escolherComodo}
        />

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
              title="por volta desta hora o corpo foi encontrado"
            >
              ✝
            </span>
            <input
              type="range"
              min={0}
              max={match.plan.hours.length - 1}
              value={hora}
              onChange={(e) => setHora(Number(e.target.value))}
              aria-label="hora da noite"
            />
          </div>
          <div className={styles.horas}>
            {match.plan.hours.map((h) => (
              <button
                key={h.interval}
                className={[
                  h.interval === hora ? styles.horaAgora : styles.hora,
                  h.interval === match.plan.crime_interval ? styles.horaCrime : '',
                ]
                  .filter(Boolean)
                  .join(' ')}
                onClick={() => setHora(h.interval)}
              >
                {h.label}
              </button>
            ))}
          </div>
        </div>
      </div>
  )

  const grade = (
      <div className={styles.coluna}>
        <p className={styles.instrucao}>
          {celula
            ? `Onde ${match.cast.find((p) => p.id === celula.suspeito)?.name} disse que estava às ${match.plan.hours[celula.hora]?.label}? Clique num cômodo.`
            : 'Clique numa célula e depois num cômodo. Isto é seu caderno — nada aqui vem do jogo.'}
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
                    <td key={h.interval}>
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
                        title={comodo ? nomeDoComodo.get(comodo) : 'sem anotação'}
                      >
                        {comodo ? nomeDoComodo.get(comodo)?.slice(0, 3) : '·'}
                      </button>
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
    </div>
  )
}
