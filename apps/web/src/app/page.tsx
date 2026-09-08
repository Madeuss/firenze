'use client'

import { CircleHelp } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useState } from 'react'

import { regras } from '@/components/Rules'
import { startMatch } from '@/lib/api'
import { Idioma } from '@/lib/idioma'
import { IDIOMAS, textos, type Locale } from '@/lib/textos'

import styles from './page.module.css'

export default function Start() {
  // O idioma é escolhido aqui porque aqui é o único lugar onde ele ainda pode
  // ser escolhido: ele vira propriedade da partida e não muda depois
  // (ADR-0005). Trocar no meio deixaria um caderno bilíngue — o que o suspeito
  // já disse continuaria no idioma em que foi dito.
  const [locale, setLocale] = useState<Locale>('pt-BR')
  const t = textos(locale)

  return (
    <Idioma locale={locale}>
      <Inicio locale={locale} aoTrocarIdioma={setLocale} t={t} />
    </Idioma>
  )
}

function Inicio({
  locale,
  aoTrocarIdioma,
  t,
}: {
  locale: Locale
  aoTrocarIdioma: (locale: Locale) => void
  t: ReturnType<typeof textos>
}) {
  const router = useRouter()
  const [seed, setSeed] = useState('')
  const [starting, setStarting] = useState(false)
  const [explaining, setExplaining] = useState(false)
  const [failure, setFailure] = useState<string | null>(null)

  async function begin() {
    setStarting(true)
    setFailure(null)
    try {
      // Semente em branco é uma noite qualquer. A mesma semente é sempre o
      // mesmo mistério (ADR-0004), então quem quiser repetir um caso pode.
      const chosen =
        seed.trim() === '' ? Math.floor(Math.random() * 100_000) : Number(seed)
      const match = await startMatch(chosen, locale)
      router.push(`/partida/${match.id}`)
    } catch (error) {
      setFailure(error instanceof Error ? error.message : t['inicio.falha'])
      setStarting(false)
    }
  }

  return (
    <main className={styles.page}>
      <div className={styles.card}>
        <h1 className={styles.title}>Firenze</h1>
        {/* O mesmo texto do modal de ajuda, vindo do catálogo em vez de
            repetido: duas cópias de uma regra divergem na primeira vez que uma
            delas muda. */}
        <p className={`prose ${styles.pitch}`}>{t['regras.pitch']}</p>
        <ul className={`${styles.rules} muted`}>
          {regras(t).map((regra) => (
            <li key={regra}>{regra}</li>
          ))}
        </ul>

        <div className={styles.actions}>
          <label className={styles.seed}>
            <span className="faint">
              {t['inicio.semente']}
              <button
                type="button"
                className={styles.about}
                onClick={() => setExplaining((open) => !open)}
                aria-expanded={explaining}
                aria-label={t['inicio.semente.pergunta']}
              >
                <CircleHelp size={14} strokeWidth={1.75} />
              </button>
            </span>
            <input
              className="mono"
              value={seed}
              onChange={(event) =>
                setSeed(event.target.value.replace(/\D/g, ''))
              }
              placeholder={t['inicio.semente.qualquer']}
              inputMode="numeric"
              aria-label={t['inicio.semente.rotulo']}
            />
          </label>

          <label className={styles.idioma}>
            <span className="faint" title={t['inicio.idioma.aviso']}>
              {t['inicio.idioma']}
            </span>
            <select
              value={locale}
              onChange={(event) =>
                aoTrocarIdioma(event.target.value as Locale)
              }
              aria-label={t['inicio.idioma.rotulo']}
            >
              {IDIOMAS.map((idioma) => (
                <option key={idioma.id} value={idioma.id}>
                  {idioma.nome}
                </option>
              ))}
            </select>
          </label>

          <button className={styles.begin} onClick={begin} disabled={starting}>
            {starting ? t['inicio.abrindo'] : t['inicio.comecar']}
          </button>
        </div>

        {explaining ? (
          <p className={styles.about_text}>{t['inicio.semente.texto']}</p>
        ) : null}

        {failure ? <p className={styles.failure}>{failure}</p> : null}
      </div>
    </main>
  )
}
