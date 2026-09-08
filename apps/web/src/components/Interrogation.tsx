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

import { ask, confront, readMatch, type MatchState } from "@/lib/api";

import Accusation from "./Accusation";
import Rules from "./Rules";
import styles from "./Interrogation.module.css";

const STANCE_LABEL: Record<string, string> = {
  cooperative: "cooperativo",
  evasive: "evasivo",
  hostile: "hostil",
  broken: "quebrado",
};

export default function Interrogation({ matchId }: { matchId: string }) {
  const [match, setMatch] = useState<MatchState | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [armed, setArmed] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [showing, setShowing] = useState<"rules" | "accusation" | null>(null);
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

  // Uma fonte só. A primeira versão guardava uma cópia local de cada resposta
  // ao lado do caderno, e todo turno respondido aparecia duas vezes assim que
  // o recarregamento chegava. O caderno da API já é o registro inteiro —
  // inclusive os turnos que não produziram nada (RN-030).
  const thread = useMemo(
    () => match?.notebook.filter((entry) => entry.character === selected) ?? [],
    [match, selected],
  );

  useEffect(() => {
    foot.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [thread.length, pending]);

  const refresh = useCallback(
    () =>
      readMatch(matchId)
        .then(setMatch)
        .catch(() => undefined),
    [matchId],
  );

  async function send() {
    if (!selected || pending) return;
    setFailure(null);
    setPending(true);
    try {
      if (armed) {
        await confront(matchId, selected, armed);
        setArmed(null);
      } else {
        const asked = question.trim();
        if (!asked) return;
        await ask(matchId, selected, asked);
        setQuestion("");
      }
      await refresh();
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
        <button
          className={styles.help}
          onClick={() => setShowing("rules")}
          aria-label="como se joga"
          title="como se joga"
        >
          ?
        </button>
        {/* Sempre visível: acusar no turno 1 é jogada legítima, e vale mais
            pontos de rapidez se der certo (RN-033). */}
        <button className={styles.accuse} onClick={() => setShowing("accusation")}>
          Acusar
        </button>
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

      {showing === "rules" ? <Rules onClose={() => setShowing(null)} /> : null}
      {showing === "accusation" ? (
        <Accusation match={match} onClose={() => setShowing(null)} />
      ) : null}
    </main>
  );
}

function textOf(match: MatchState, id: string): string {
  return match.known.find((fact) => fact.id === id)?.text ?? id;
}
