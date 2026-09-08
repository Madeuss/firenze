'use client'

/**
 * O seletor de cômodo de uma célula da grade.
 *
 * A grade e a planta são duas formas de dizer a mesma coisa, e antes disto só
 * uma delas conseguia dizer: para preencher uma célula era preciso clicar nela
 * e depois num cômodo da planta. Com as duas em abas, a planta pode não estar
 * na tela — então a célula passa a bastar sozinha.
 *
 * Um campo de filtro em vez de um `<select>` nativo: com oito cômodos ainda é
 * pouco, mas quem digita "por" e aperta Enter não tira a mão do teclado, e é
 * assim que se preenche uma grade inteira sem sofrer.
 */

import { useEffect, useMemo, useRef, useState } from 'react'

import { useTextos } from '@/lib/idioma'

import styles from './EscolherComodo.module.css'

export type Comodo = { id: string; name: string }

/** Sem acento e em minúsculas: "porão" tem que casar com "porao". */
function achatar(texto: string): string {
  return texto
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
}

export default function EscolherComodo({
  comodos,
  atual,
  aoEscolher,
  aoFechar,
}: {
  comodos: readonly Comodo[]
  atual: string | null
  /** `null` apaga a anotação. */
  aoEscolher: (comodo: string | null) => void
  aoFechar: () => void
}) {
  const t = useTextos()
  const [filtro, setFiltro] = useState('')
  const caixa = useRef<HTMLDivElement>(null)

  // Clicar fora fecha. Sem isto, abrir uma célula e desistir dela obrigava a
  // voltar e clicar de novo exatamente no mesmo lugar.
  useEffect(() => {
    function fora(evento: PointerEvent) {
      if (!caixa.current?.contains(evento.target as Node)) aoFechar()
    }
    // No próximo quadro: o clique que abriu esta caixa ainda está subindo.
    const quadro = requestAnimationFrame(() =>
      document.addEventListener('pointerdown', fora),
    )
    return () => {
      cancelAnimationFrame(quadro)
      document.removeEventListener('pointerdown', fora)
    }
  }, [aoFechar])

  const achados = useMemo(() => {
    const busca = achatar(filtro.trim())
    if (!busca) return comodos
    return comodos.filter((c) => achatar(c.name).includes(busca))
  }, [comodos, filtro])

  return (
    <div ref={caixa} className={styles.caixa} role="dialog" aria-label={t['comodo.dialogo']}>
      <input
        className={styles.filtro}
        value={filtro}
        onChange={(e) => setFiltro(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Escape') {
            e.preventDefault()
            aoFechar()
          }
          if (e.key === 'Enter') {
            e.preventDefault()
            const primeiro = achados[0]
            if (primeiro) aoEscolher(primeiro.id)
          }
        }}
        placeholder={t['comodo.filtro']}
        aria-label={t['comodo.filtro.rotulo']}
        autoFocus
      />

      <ul className={styles.lista}>
        {achados.map((comodo) => (
          <li key={comodo.id}>
            <button
              className={comodo.id === atual ? styles.itemAgora : styles.item}
              onClick={() => aoEscolher(comodo.id)}
            >
              {comodo.name}
            </button>
          </li>
        ))}
        {achados.length === 0 ? (
          <li className={styles.nada}>{t['comodo.nenhum']}</li>
        ) : null}
      </ul>

      {atual ? (
        <button className={styles.limpar} onClick={() => aoEscolher(null)}>
          {t['comodo.apagar']}
        </button>
      ) : null}
    </div>
  )
}
