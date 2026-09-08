"use client";

/**
 * Modo Interrogatório: elenco, conversa, e o único campo de texto do jogo.
 *
 * O que esta tela não faz é tão importante quanto o que ela faz. Ela não
 * mostra `mentiu`, não mostra em que fato a resposta se apoiou, e não sabe o
 * que foi alegado — a API não devolve nada disso durante a partida, e é por
 * isso que a dedução é do jogador. Ver docs/03-casos-de-uso.md.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ask, confront, readMatch, type Answer, type MatchState } from "@/lib/api";

import styles from "./Interrogation.module.css";

const STANCE_LABEL: Record<string, string> = {
  cooperative: "cooperativo",
  evasive: "evasivo",
  hostile: "hostil",
  broken: "quebrado",
};

/** Um turno que não produziu fala. Nunca vira desculpa em personagem: uma
 * falha de sistema apareceria como pista, e o jogador tiraria conclusão dela. */
type Silence = { turn: "silence"; character: string };
type Spoken = { turn: "spoken"; character: string; question: string; line: string };
type Entry = Spoken | Silence;

export default function Interrogation({ matchId }: { matchId: string }) {
  const [match, setMatch] = useState<MatchState | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [armed, setArmed] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [extra, setExtra] = useState<Entry[]>([]);
  const [failure, setFailure] = useState<string | null>(null);
  const foot = useRef<HTMLDivElement>(null);

  useEffect(() => {
    readMatch(matchId)
      .then((state) => {
        setMatch(state);
        const first = state.cast.find((person) => person.role === "suspect");
        setSelected((current) => current ?? first?.id ?? null);
      })
      .catch((error: unknown) =>
        setFailure(error instanceof Error ? error.message : "não deu para abrir a partida"),
      );
  }, [matchId]);

  const suspects = useMemo(
    () => match?.cast.filter((person) => person.role === "suspect") ?? [],
    [match],
  );

  const thread = useMemo<Entry[]>(() => {
    if (!match || !selected) return [];
    const said = match.notebook
      .filter((line) => line.character === selected)
      .map<Entry>((line) => ({
        turn: "spoken",
        character: line.character,
        question: line.question,
        line: line.line,
      }));
    return [...said, ...extra.filter((entry) => entry.character === selected)];
  }, [match, selected, extra]);

  useEffect(() => {
    foot.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [thread.length, pending]);

  const record = useCallback(
    (answer: Answer, asked: string) => {
      setExtra((current) => [
        ...current,
        answer.answered && answer.line
          ? { turn: "spoken", character: answer.character, question: asked, line: answer.line }
          : { turn: "silence", character: answer.character },
      ]);
      // O caderno oficial é o da API. Recarregar depois de cada turno mantém
      // postura, provas e turnos restantes vindo de uma fonte só.
      readMatch(matchId)
        .then(setMatch)
        .catch(() => undefined);
    },
    [matchId],
  );

  async function send() {
    if (!selected || pending) return;
    setFailure(null);
    setPending(true);
    try {
      if (armed) {
        const answer = await confront(matchId, selected, armed);
        record(answer, `apresentou ${armed}`);
        setArmed(null);
      } else {
        const asked = question.trim();
        if (!asked) return;
        const answer = await ask(matchId, selected, asked);
        setQuestion("");
        record(answer, asked);
      }
    } catch (error) {
      setFailure(error instanceof Error ? error.message : "não deu para perguntar");
    } finally {
      setPending(false);
    }
  }

  if (failure && !match) return <main className={styles.empty}>{failure}</main>;
  if (!match || !selected) return <main className={styles.empty} />;

  const current = suspects.find((person) => person.id === selected);
  const stance = current?.stance ?? null;
  const spent = armed ? 2 : 1;
  const broke = match.turns_left < spent;

  return (
    <main className={styles.screen}>
      <header className={styles.top}>
        <span className={styles.case}>
          Caso <span className="mono">{match.seed}</span>
        </span>
        <span className={styles.briefing}>{match.known[0]?.text}</span>
        <span className={styles.turns}>
          <strong>{match.turns_left}</strong> turnos
        </span>
      </header>

      <div className={styles.body}>
        <nav className={styles.cast} aria-label="elenco">
          {suspects.map((person) => (
            <button
              key={person.id}
              className={person.id === selected ? styles.pickedName : styles.name}
              onClick={() => setSelected(person.id)}
            >
              <span
                className={styles.dot}
                data-stance={person.stance ?? "unasked"}
                aria-hidden="true"
              />
              {person.name}
            </button>
          ))}
        </nav>

        <section className={styles.conversation}>
          <div className={styles.who}>
            <h2>{current?.name}</h2>
            {stance ? (
              <span className={styles.stance} data-stance={stance}>
                {STANCE_LABEL[stance]}
              </span>
            ) : (
              <span className="faint">ainda não falou com você</span>
            )}
          </div>

          <div className={styles.thread}>
            {thread.length === 0 ? (
              <p className={`prose ${styles.nothing}`}>
                Ninguém disse nada ainda. Pergunte alguma coisa.
              </p>
            ) : null}

            {thread.map((entry, index) =>
              entry.turn === "spoken" ? (
                <article key={index} className={styles.exchange}>
                  <p className={styles.asked}>{entry.question}</p>
                  <p className={`prose ${styles.line}`}>{entry.line}</p>
                </article>
              ) : (
                <article key={index} className={styles.silence}>
                  <p>Não veio resposta. O turno foi gasto.</p>
                </article>
              ),
            )}

            {pending ? <p className={styles.waiting}>…</p> : null}
            <div ref={foot} />
          </div>

          <div className={styles.compose}>
            {armed ? (
              <div className={styles.armed}>
                <span>
                  apresentar <span className="mono">{armed}</span>
                </span>
                <button className={styles.disarm} onClick={() => setArmed(null)}>
                  cancelar
                </button>
              </div>
            ) : (
              <textarea
                className={styles.input}
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    void send();
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
              disabled={pending || broke || (!armed && question.trim() === "")}
            >
              {armed ? "Confrontar — custa 2 turnos" : "Perguntar"}
            </button>
          </div>

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
        </section>
      </div>
    </main>
  );
}

function textOf(match: MatchState, id: string): string {
  return match.known.find((fact) => fact.id === id)?.text ?? id;
}
