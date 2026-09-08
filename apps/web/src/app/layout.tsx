import type { Metadata } from 'next'
import { Inter, Old_Standard_TT, Lora, Rubik_Glitch } from 'next/font/google'

import './globals.css'

// Serifada para a fala, sem serifa para a interface, monoespaçada para id de
// fato. Três papéis, três fontes, nenhuma decorativa.
const prose = Lora({
  subsets: ['latin', 'latin-ext'],
  variable: '--font-prose',
  display: 'swap',
})

const rubik = Rubik_Glitch({
  subsets: ['latin', 'latin-ext'],
  variable: '--font-rubik',
  weight: '400',
  display: 'swap',
})

const ui = Inter({
  subsets: ['latin', 'latin-ext'],
  variable: '--font-ui',
  display: 'swap',
})

const mono = Old_Standard_TT({
  subsets: ['latin', 'latin-ext'],
  variable: '--font-mono',
  weight: '400',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'Firenze',
  description: 'Um mistério onde os suspeitos respondem.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html
      lang="pt-BR"
      className={`${prose.variable} ${ui.variable} ${mono.variable} ${rubik.variable}`}
    >
      <body>{children}</body>
    </html>
  )
}
