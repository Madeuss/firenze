'use client'

/**
 * Modo Interrogatório: elenco, conversa, e o único campo de texto do jogo.
 *
 * O que esta tela não faz é tão importante quanto o que ela faz. Ela não
 * mostra `mentiu`, não mostra em que fato a resposta se apoiou, e não sabe o
 * que foi alegado — a API não devolve nada disso durante a partida, e é por
 * isso que a dedução é do jogador. Ver docs/03-casos-de-uso.md.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { ask, confront, readMatch, type MatchState } from '@/lib/api'

import Accusation from './Accusation'
import Deducao from './Deducao'
import Retrato from './Retrato'
import Rules from './Rules'
import styles from './Interrogation.module.css'

const STANCE_LABEL: Record<string, string> = {
  cooperative: 'cooperativo',
  evasive: 'evasivo',
  hostile: 'hostil',
  broken: 'quebrado',
}

export default function Interrogation({ matchId }: { matchId: string }) {
  const [match, setMatch] = useState<MatchState | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [question, setQuestion] = useState('')
  const [armed, setArmed] = useState<string | null>(null)
  const [pending, setPending] = useState(false)
  const [failure, setFailure] = useState<string | null>(null)
  const [showing, setShowing] = useState<'rules' | 'accusation' | null>(null)
  // Perguntar custa turno; pensar nao custa nada. A interface nomeia isso.
  const [modo, setModo] = useState<'interrogatorio' | 'deducao'>('interrogatorio')
  const rolagem = useRef<HTMLDivElement>(null)
  // `pending` e estado, e estado nao muda a tempo: dois Enter seguidos passam
  // os dois pela guarda antes do primeiro render. Este trava na hora.
  const enviando = useRef(false)
  // Duas leituras da partida podem voltar fora de ordem, e a mais velha
  // sobrescreveria a mais nova — o turno recem-gasto sumia da conversa.
  const leitura = useRef(0)

  useEffect(() => {
    const minha = ++leitura.current
    readMatch(matchId)
      .then((state) => {
        if (minha !== leitura.current) return
        setMatch(state)
        const first = state.cast.find((person) => person.role === 'suspect')
        setSelected((current) => current ?? first?.id ?? null)
      })
      .catch((error: unknown) =>
        setFailure(
          error instanceof Error
            ? error.message
            : 'não deu para abrir a partida',
        ),
      )
  }, [matchId])

  const suspects = useMemo(
    () => match?.cast.filter((person) => person.role === 'suspect') ?? [],
    [match],
  )

  // Uma fonte só. A primeira versão guardava uma cópia local de cada resposta
  // ao lado do caderno, e todo turno respondido aparecia duas vezes assim que
  // o recarregamento chegava. O caderno da API já é o registro inteiro —
  // inclusive os turnos que não produziram nada (RN-030).
  const thread = useMemo(
    () => match?.notebook.filter((entry) => entry.character === selected) ?? [],
    [match, selected],
  )

  // Rola a conversa, e só ela. `scrollIntoView` mexia na página inteira, e com
  // o cabeçalho e o campo de texto agora fixos não há página para rolar.
  useEffect(() => {
    const caixa = rolagem.current
    if (caixa) caixa.scrollTop = caixa.scrollHeight
  }, [thread.length, pending, selected])

  const refresh = useCallback(async () => {
    const minha = ++leitura.current
    try {
      const estado = await readMatch(matchId)
      if (minha === leitura.current) setMatch(estado)
    } catch {
      // Recarregar e conforto; o turno ja aconteceu no servidor de todo jeito.
    }
  }, [matchId])

  async function send() {
    if (!selected || enviando.current) return
    enviando.current = true
    setFailure(null)
    setPending(true)
    try {
      if (armed) {
        await confront(matchId, selected, armed)
        setArmed(null)
      } else {
        const asked = question.trim()
        if (!asked) return
        await ask(matchId, selected, asked)
        setQuestion('')
      }
      await refresh()
    } catch (error) {
      setFailure(
        error instanceof Error ? error.message : 'não deu para perguntar',
      )
    } finally {
      enviando.current = false
      setPending(false)
    }
  }

  if (failure && !match) return <main className={styles.empty}>{failure}</main>
  if (!match || !selected) return <main className={styles.empty} />

  const current = suspects.find((person) => person.id === selected)
  const stance = current?.stance ?? null
  const spent = armed ? 2 : 1
  const broke = match.turns_left < spent

  return (
    <main className={styles.screen}>
      <header className={styles.top}>
        <span className={styles.case}>
          Caso <span className="mono">{match.seed}</span>
        </span>
        <span className={styles.briefing}>
          {match.known[0]?.text}
          <button
            className={styles.help}
            onClick={() => setShowing('rules')}
            aria-label="como se joga"
            title="como se joga"
          >
            ?
          </button>
        </span>
        <span className={styles.turns}>
          <strong>{match.turns_left}</strong> turnos
        </span>
        <div className={styles.modos}>
          <button
            className={modo === 'interrogatorio' ? styles.modoAgora : styles.modo}
            onClick={() => setModo('interrogatorio')}
          >
            Interrogatório
          </button>
          <button
            className={modo === 'deducao' ? styles.modoAgora : styles.modo}
            onClick={() => setModo('deducao')}
            title="não gasta turno"
          >
            Dedução
          </button>
        </div>
        {/* Sempre visível: acusar no turno 1 é jogada legítima, e vale mais
            pontos de rapidez se der certo (RN-033). */}
        <button
          className={styles.accuse}
          onClick={() => setShowing('accusation')}
        >
          Acusar
        </button>
      </header>

      {modo === 'deducao' ? (
        <div className={styles.pensar}>
          <Deducao match={match} />
        </div>
      ) : (
      <div className={styles.body}>
        <nav className={styles.cast} aria-label="elenco">
          {suspects.map((person) => (
            <button
              key={person.id}
              className={
                person.id === selected ? styles.pickedName : styles.name
              }
              onClick={() => setSelected(person.id)}
            >
              <Retrato
                nome={person.name}
                tamanho={44}
                aceso={person.id === selected}
              />
              <span className={styles.quem}>
                <span className={styles.linhaNome}>
                  {person.name}
                  <span
                    className={styles.dot}
                    data-stance={person.stance ?? 'unasked'}
                    aria-hidden="true"
                  />
                </span>
                {/* A função identifica melhor que o nome: numa casa de dez
                    pessoas, lembrar "a cozinheira" é mais fácil que lembrar
                    "Ilma Prado". */}
                {person.occupation ? (
                  <span className={styles.funcao}>{person.occupation}</span>
                ) : null}
              </span>
            </button>
          ))}
        </nav>

        <section className={styles.conversation}>
          {/* Fixo, como o cabeçalho de uma conversa: quem é, o que faz na casa
              e como está segurando as pontas. Nada aqui rola junto com a
              conversa, porque é o que responde "com quem estou falando". */}
          <header className={styles.who}>
            {current ? <Retrato nome={current.name} tamanho={52} /> : null}
            <div className={styles.quemFala}>
              <h2>{current?.name}</h2>
              {current?.occupation ? (
                <span className={styles.funcao}>{current.occupation}</span>
              ) : null}
            </div>
            {stance ? (
              <span className={styles.stance} data-stance={stance}>
                {STANCE_LABEL[stance]}
              </span>
            ) : (
              <span className="faint">ainda não falou com você</span>
            )}
          </header>

          <div className={styles.thread} ref={rolagem}>
            {thread.length === 0 ? (
              <p className={`prose ${styles.nothing}`}>
                Ninguém disse nada ainda. Pergunte alguma coisa.
              </p>
            ) : null}

            {thread.map((entry) =>
              entry.answered ? (
                <article key={entry.turn} className={styles.exchange}>
                  <p className={styles.asked}>{entry.question}</p>
                  <p className={`prose ${styles.line}`}>{entry.line}</p>
                </article>
              ) : (
                <article key={entry.turn} className={styles.silence}>
                  <p className={styles.asked}>{entry.question}</p>
                  <p>Não veio resposta. O turno foi gasto.</p>
                </article>
              ),
            )}

            {pending ? <p className={styles.waiting}>…</p> : null}
          </div>

          <div className={styles.rodape}>
            {failure ? <p className={styles.failure}>{failure}</p> : null}
            {broke ? (
              <p className={styles.failure}>
                Turnos insuficientes. Só resta acusar.
              </p>
            ) : null}

            <div className={styles.evidence}>
              <span className="faint">provas</span>
              {match.evidence.length === 0 ? (
                <span className="faint">— nada nas mãos ainda</span>
              ) : (
                match.evidence.map((id) => (
                  <button
                    key={id}
                    className={id === armed ? styles.pickedCard : styles.card}
                    onClick={() => setArmed(id === armed ? null : id)}
                    title={textOf(match, id)}
                  >
                    <span className="mono">{id}</span>
                  </button>
                ))
              )}
            </div>

            <div className={styles.compose}>
              {armed ? (
                <div className={styles.armed}>
                  <span>
                    apresentar <span className="mono">{armed}</span>
                  </span>
                  <button
                    className={styles.disarm}
                    onClick={() => setArmed(null)}
                  >
                    cancelar
                  </button>
                </div>
              ) : (
                <textarea
                  className={styles.input}
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' && !event.shiftKey) {
                      event.preventDefault()
                      void send()
                    }
                  }}
                  placeholder="pergunte alguma coisa…"
                  maxLength={500}
                  rows={2}
                  aria-label="sua pergunta"
                />
              )}
              <button
                className={styles.send}
                onClick={() => void send()}
                disabled={pending || broke || (!armed && question.trim() === '')}
              >
                {armed ? 'Confrontar — custa 2 turnos' : 'Perguntar'}
              </button>
            </div>
          </div>
        </section>
      </div>
      )}

      {showing === 'rules' ? <Rules onClose={() => setShowing(null)} /> : null}
      {showing === 'accusation' ? (
        <Accusation match={match} onClose={() => setShowing(null)} />
      ) : null}
    </main>
  )
}

function textOf(match: MatchState, id: string): string {
  return match.known.find((fact) => fact.id === id)?.text ?? id
}
