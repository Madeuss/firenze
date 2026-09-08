'use client'

/**
 * As regras, onde elas fazem falta.
 *
 * O mesmo texto que a tela inicial mostra, que some no primeiro clique. Um
 * jogador dez turnos adiante não deveria ter que lembrar quanto custa um
 * confronto.
 */

import type { Textos } from '@/lib/textos'
import { useTextos } from '@/lib/idioma'

import styles from './Rules.module.css'

/** As quatro regras, na ordem em que doem. */
export function regras(t: Textos): readonly string[] {
  return [t['regras.turnos'], t['regras.confronto'], t['regras.pensar'], t['regras.acusacao']]
}

export default function Rules({ onClose }: { onClose: () => void }) {
  const t = useTextos()

  return (
    <div
      className={styles.backdrop}
      role="dialog"
      aria-modal="true"
      aria-label={t['regras.como']}
    >
      <div className={styles.sheet}>
        <h2 className={styles.title}>{t['regras.titulo']}</h2>
        <p className={`prose ${styles.pitch}`}>{t['regras.pitch']}</p>
        <ul className={styles.rules}>
          {regras(t).map((regra) => (
            <li key={regra}>{regra}</li>
          ))}
        </ul>
        <div className={styles.actions}>
          <button className={styles.primary} onClick={onClose} autoFocus>
            {t['regras.entendi']}
          </button>
        </div>
      </div>
    </div>
  )
}
