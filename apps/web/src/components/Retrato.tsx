/**
 * O retrato de um suspeito, aceso ou apagado.
 *
 * Os onze arquivos vieram de duas famílias visuais — uns mais quentes e mais
 * pintados, outros mais chapados e frios — e o enquadramento varia: a cabeça
 * do Bartolomeu ocupa 44% do quadro, a do Godofredo 4%. Nada disso se conserta
 * regerando arte. Aqui a normalização é de tela: saturação e brilho puxados
 * para o mesmo lugar, e recorte pelo topo, que é onde a cabeça sempre está.
 *
 * Apagado é opacidade e cinza. Com a paleta quase monocromática destes
 * retratos, `grayscale` sozinho quase não muda nada — quem faz o trabalho é a
 * opacidade.
 */

import { iniciais, retratoDe } from "@/lib/retratos";

import styles from "./Retrato.module.css";

export default function Retrato({
  nome,
  tamanho,
  aceso = true,
}: {
  nome: string;
  tamanho: number;
  aceso?: boolean;
}) {
  const fonte = retratoDe(nome);
  const classe = `${styles.moldura} ${aceso ? styles.aceso : styles.apagado}`;

  if (!fonte) {
    return (
      <span className={classe} style={{ width: tamanho, height: tamanho }} aria-hidden="true">
        <span className={styles.iniciais}>{iniciais(nome)}</span>
      </span>
    );
  }

  return (
    <span className={classe} style={{ width: tamanho, height: tamanho }}>
      {/* eslint-disable-next-line @next/next/no-img-element -- asset local, sem otimização remota */}
      <img className={styles.face} src={fonte} alt="" width={tamanho} height={tamanho} />
    </span>
  );
}
