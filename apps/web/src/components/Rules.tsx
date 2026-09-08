'use client'

/**
 * As regras, onde elas fazem falta.
 *
 * O mesmo texto que a tela inicial mostra, que some no primeiro clique. Um
 * jogador dez turnos adiante não deveria ter que lembrar quanto custa um
 * confronto.
 */

import styles from './Rules.module.css'

export const PITCH =
  'Um homem foi encontrado morto na própria casa. Seis pessoas estavam lá, e ' +
  'todas têm o que esconder — só uma esconde o assassinato.'

export const RULES: readonly string[] = [
  'Trinta turnos para perguntar. Cada pergunta gasta um.',
  'Confrontar alguém com uma prova custa dois, e só vale com prova que você tem.',
  'Pensar não custa nada. Trocar de suspeito e reler o caderno são de graça.',
  'Uma acusação por partida, e ela não volta atrás.',
]

export default function Rules({ onClose }: { onClose: () => void }) {
  return (
    <div
      className={styles.backdrop}
      role="dialog"
      aria-modal="true"
      aria-label="como se joga"
    >
      <div className={styles.sheet}>
        <h2 className={styles.title}>Como se joga</h2>
        <p className={`prose ${styles.pitch}`}>{PITCH}</p>
        <ul className={styles.rules}>
          {RULES.map((rule) => (
            <li key={rule}>{rule}</li>
          ))}
        </ul>
        <div className={styles.actions}>
          <button className={styles.primary} onClick={onClose} autoFocus>
            Entendi
          </button>
        </div>
      </div>
    </div>
  )
}
