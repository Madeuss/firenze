/**
 * Se a tela comporta a mesa inteira — elenco, conversa e painel lado a lado.
 *
 * Podia ser só uma media query, e não é por um motivo: numa tela estreita a
 * planta 3D não deve ficar escondida com `display: none`, deve **não existir**.
 * Um canvas escondido continua montado, continua carregando modelo e continua
 * ocupando memória de vídeo num aparelho que provavelmente tem pouca. Então
 * quem decide é o JavaScript, e a árvore muda de verdade.
 *
 * `useSyncExternalStore` porque essa é a forma que o React 19 quer para ler
 * qualquer coisa que vive fora dele — o mesmo caminho que `notas.ts` usa.
 */

import { useSyncExternalStore } from 'react'

/** Abaixo disto a conversa e a planta não cabem juntas sem apertar as duas. */
export const LARGURA_DA_MESA = '(min-width: 78rem)'

function assinar(mudou: () => void): () => void {
  const consulta = window.matchMedia(LARGURA_DA_MESA)
  consulta.addEventListener('change', mudou)
  return () => consulta.removeEventListener('change', mudou)
}

function agora(): boolean {
  return window.matchMedia(LARGURA_DA_MESA).matches
}

/** No servidor não há tela; a versão estreita é a que não depende de nada. */
function noServidor(): boolean {
  return false
}

export function useTelaLarga(): boolean {
  return useSyncExternalStore(assinar, agora, noServidor)
}
