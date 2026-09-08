"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { startMatch } from "@/lib/api";

import styles from "./page.module.css";

export default function Start() {
  const router = useRouter();
  const [seed, setSeed] = useState("");
  const [starting, setStarting] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  async function begin() {
    setStarting(true);
    setFailure(null);
    try {
      // Semente em branco é uma noite qualquer. A mesma semente é sempre o
      // mesmo mistério (ADR-0004), então quem quiser repetir um caso pode.
      const chosen = seed.trim() === "" ? Math.floor(Math.random() * 100_000) : Number(seed);
      const match = await startMatch(chosen);
      router.push(`/partida/${match.id}`);
    } catch (error) {
      setFailure(error instanceof Error ? error.message : "não deu para começar");
      setStarting(false);
    }
  }

  return (
    <main className={styles.page}>
      <div className={styles.card}>
        <h1 className={styles.title}>Firenze</h1>
        <p className={`prose ${styles.pitch}`}>
          Um homem foi encontrado morto na própria casa. Seis pessoas estavam lá, e
          todas têm o que esconder — só uma esconde o assassinato.
        </p>
        <p className={`${styles.rules} muted`}>
          Trinta turnos para perguntar. Confrontar alguém com uma prova custa dois.
          Pensar não custa nada.
        </p>

        <div className={styles.actions}>
          <label className={styles.seed}>
            <span className="faint">semente</span>
            <input
              className="mono"
              value={seed}
              onChange={(event) => setSeed(event.target.value.replace(/\D/g, ""))}
              placeholder="qualquer"
              inputMode="numeric"
              aria-label="semente do caso, opcional"
            />
          </label>
          <button className={styles.begin} onClick={begin} disabled={starting}>
            {starting ? "abrindo a casa…" : "Começar investigação"}
          </button>
        </div>

        {failure ? <p className={styles.failure}>{failure}</p> : null}
      </div>
    </main>
  );
}
