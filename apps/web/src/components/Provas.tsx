'use client'

/**
 * O que o jogador tem na mão, para ler.
 *
 * Havia um único lugar onde as provas apareciam por extenso: o formulário de
 * acusação, atrás de dois cliques e de um botão chamado **Acusar**. Para
 * reler o que arrancou de alguém, o jogador tinha que abrir a tela que encerra
 * a partida — e sair dela pelo "voltar", torcendo para não ter clicado errado.
 *
 * A separação que esta aba faz é entre **o que a casa deu** e **o que você
 * arrancou**. A primeira lista veio de graça no briefing; a segunda é o placar
 * real do interrogatório, e é dela que sai uma acusação com pontos de prova.
 */

import type { MatchState } from '@/lib/api'
import { useTextos } from '@/lib/idioma'

import styles from './Provas.module.css'

export default function Provas({ match }: { match: MatchState }) {
  const t = useTextos()
  const publicos = new Set(match.known.map((fato) => fato.id))
  const arrancadas = match.evidence.filter((prova) => !publicos.has(prova.id))

  return (
    <div className={styles.dossie}>
      <section>
        <h3 className={styles.titulo}>{t['provas.sabidas']}</h3>
        <ul className={styles.lista}>
          {match.known.map((fato) => (
            <li key={fato.id} className={styles.fato}>
              <span className="mono">{fato.id}</span>
              <span>{fato.text}</span>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h3 className={styles.titulo}>{t['provas.arrancadas']}</h3>
        {arrancadas.length === 0 ? (
          <p className={styles.vazio}>{t['provas.nenhuma']}</p>
        ) : (
          <ul className={styles.lista}>
            {arrancadas.map((prova) => (
              <li key={prova.id} className={styles.fato}>
                <span className="mono">{prova.id}</span>
                <span>{prova.text}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
