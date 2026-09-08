'use client'

/**
 * Em que idioma a moldura fala.
 *
 * Dentro de uma partida a resposta não é uma preferência: é `match.locale`, que
 * o servidor fixou quando a partida foi criada (ADR-0005). Interface num idioma
 * e caso em outro seria pior que ter só um — o jogador leria um botão em
 * inglês para ouvir um mordomo em português.
 *
 * Por isso um contexto, e não um seletor global: quem entra numa partida herda
 * o idioma dela, e a única tela que *escolhe* é a inicial, onde a partida ainda
 * não existe.
 */

import { createContext, useContext, type ReactNode } from 'react'

import { textos, type Textos } from './textos'

const Contexto = createContext<Textos>(textos('pt-BR'))

export function Idioma({
  locale,
  children,
}: {
  locale: string
  children: ReactNode
}) {
  return (
    <Contexto.Provider value={textos(locale)}>{children}</Contexto.Provider>
  )
}

export function useTextos(): Textos {
  return useContext(Contexto)
}
