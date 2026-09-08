"use client";

/**
 * A acusação: escrever, conferir, confirmar.
 *
 * A tela do Golden Idol. O jogador escreve com as próprias palavras, o parser
 * preenche as lacunas, e **nada acontece até ele confirmar os campos** — o que
 * não é gentileza do front: `POST /accusation` não aceita prosa, só campos.
 * Uma leitura errada não tem como virar acusação sem alguém ver antes (RN-031).
 *
 * O que o parser não conseguiu encaixar volta em `unresolved`, com as palavras
 * do jogador, em vez de virar palpite.
 */

import Link from "next/link";
import { useState } from "react";

import {
  accuse,
  draftAccusation,
  type DraftAccusation,
  type MatchState,
  type Outcome,
} from "@/lib/api";
import { useTextos } from "@/lib/idioma";
import { com, type Textos } from "@/lib/textos";

import styles from "./Accusation.module.css";

type Stage = "writing" | "checking" | "decided";

export default function Accusation({
  match,
  onClose,
}: {
  match: MatchState;
  onClose: () => void;
}) {
  const t = useTextos();
  const [stage, setStage] = useState<Stage>("writing");
  const [text, setText] = useState("");
  const [draft, setDraft] = useState<DraftAccusation | null>(null);
  const [culprit, setCulprit] = useState<string | null>(null);
  const [motive, setMotive] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<string[]>([]);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  const suspects = match.cast.filter((person) => person.role === "suspect");

  function adopt(read: DraftAccusation | null) {
    setDraft(read);
    setCulprit(read?.culprit ?? null);
    setMotive(read?.motive_key ?? null);
    setEvidence([...(read?.evidence ?? [])]);
    setStage("checking");
  }

  async function read() {
    setBusy(true);
    setFailure(null);
    try {
      adopt(await draftAccusation(match.id, text.trim()));
    } catch (error) {
      setFailure(
        error instanceof Error ? error.message : t["acusacao.falha.leitura"],
      );
    } finally {
      setBusy(false);
    }
  }

  async function commit() {
    if (!culprit) return;
    setBusy(true);
    setFailure(null);
    try {
      setOutcome(await accuse(match.id, { culprit, motive_key: motive, evidence }));
      setStage("decided");
    } catch (error) {
      setFailure(
        error instanceof Error ? error.message : t["acusacao.falha.acusar"],
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={styles.backdrop} role="dialog" aria-modal="true" aria-label={t["acusacao.dialogo"]}>
      <div className={styles.sheet}>
        {stage === "writing" ? (
          <>
            <h2 className={styles.title}>{t["acusacao.quem"]}</h2>
            <p className={`${styles.hint} muted`}>{t["acusacao.dica"]}</p>
            <textarea
              className={styles.text}
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder={t["acusacao.exemplo"]}
              maxLength={1000}
              rows={4}
              autoFocus
              aria-label={t["acusacao.rotulo"]}
            />
            <div className={styles.actions}>
              <button className={styles.ghost} onClick={onClose}>
                {t["acusacao.voltar"]}
              </button>
              <button
                className={styles.ghost}
                onClick={() => adopt(null)}
              >
                {t["acusacao.escolher"]}
              </button>
              <button
                className={styles.primary}
                onClick={() => void read()}
                disabled={busy || text.trim() === ""}
              >
                {busy ? t["acusacao.lendo"] : t["acusacao.continuar"]}
              </button>
            </div>
          </>
        ) : null}

        {stage === "checking" ? (
          <>
            <h2 className={styles.title}>{t["acusacao.confira"]}</h2>

            <label className={styles.field}>
              <span className="faint">{t["acusacao.culpado"]}</span>
              <select
                value={culprit ?? ""}
                onChange={(event) => setCulprit(event.target.value || null)}
              >
                <option value="">{t["acusacao.ninguem"]}</option>
                {suspects.map((person) => (
                  <option key={person.id} value={person.id}>
                    {person.name}
                  </option>
                ))}
              </select>
            </label>

            <label className={styles.field}>
              <span className="faint">{t["acusacao.motivo"]}</span>
              <select
                value={motive ?? ""}
                onChange={(event) => setMotive(event.target.value || null)}
                disabled={match.known_motives.length === 0}
              >
                <option value="">
                  {match.known_motives.length === 0
                    ? t["acusacao.motivo.nenhum"]
                    : t["acusacao.motivo.livre"]}
                </option>
                {match.known_motives.map((key) => (
                  <option key={key} value={key}>
                    {key}
                  </option>
                ))}
              </select>
            </label>

            <fieldset className={styles.field}>
              <legend className="faint">{t["acusacao.provas"]}</legend>
              <div className={styles.checks}>
                {match.evidence.map((id) => (
                  <label key={id} className={styles.check}>
                    <input
                      type="checkbox"
                      checked={evidence.includes(id)}
                      onChange={(event) =>
                        setEvidence((current) =>
                          event.target.checked
                            ? [...current, id]
                            : current.filter((held) => held !== id),
                        )
                      }
                    />
                    <span className="mono">{id}</span>
                  </label>
                ))}
              </div>
            </fieldset>

            {draft?.unresolved?.length ? (
              <p className={styles.unresolved}>
                {com(t["acusacao.sobrou"], {
                  itens: draft.unresolved.join("; "),
                })}
              </p>
            ) : null}

            <p className={styles.warning}>{t["acusacao.irreversivel"]}</p>

            <div className={styles.actions}>
              <button className={styles.ghost} onClick={() => setStage("writing")}>
                {t["acusacao.voltar"]}
              </button>
              <button
                className={styles.primary}
                onClick={() => void commit()}
                disabled={busy || !culprit}
              >
                {busy ? t["acusacao.acusando"] : t["acusacao.acusar"]}
              </button>
            </div>
          </>
        ) : null}

        {stage === "decided" && outcome ? <Verdict outcome={outcome} t={t} /> : null}

        {failure ? <p className={styles.failure}>{failure}</p> : null}
      </div>
    </div>
  );
}

function Verdict({ outcome, t }: { outcome: Outcome; t: Textos }) {
  return (
    <>
      <h2 className={styles.title}>
        {outcome.correct ? t["veredito.certo"] : t["veredito.errado"]}
      </h2>
      {/* A frase inteira vem do catálogo, e não montada em pedaços: a ordem
          das palavras é do idioma, não nossa. */}
      <p className={`prose ${styles.truth}`}>
        {com(t["veredito.frase"], {
          culpado: outcome.culprit,
          meio: outcome.means,
          motivo: outcome.motive,
        })}
      </p>

      {outcome.epilogue ? <p className={`prose ${styles.truth}`}>{outcome.epilogue}</p> : null}

      <dl className={styles.score}>
        <div>
          <dt>{t["veredito.culpado"]}</dt>
          <dd>{outcome.culprit_points}</dd>
        </div>
        <div>
          <dt>{t["veredito.motivo"]}</dt>
          <dd>{outcome.motive_points}</dd>
        </div>
        <div>
          <dt>{t["veredito.provas"]}</dt>
          <dd>{outcome.evidence_points}</dd>
        </div>
        <div>
          <dt>{t["veredito.rapidez"]}</dt>
          <dd>{outcome.speed_points}</dd>
        </div>
        <div className={styles.total}>
          <dt>{t["veredito.total"]}</dt>
          <dd>{outcome.score}</dd>
        </div>
      </dl>

      <div className={styles.actions}>
        <Link className={styles.primary} href="/">
          {t["veredito.nova"]}
        </Link>
      </div>
    </>
  );
}
