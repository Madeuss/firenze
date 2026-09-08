/**
 * Qual retrato pertence a quem.
 *
 * A chave é o **nome**, nunca o id. O gerador embaralha os nomes a cada
 * semente, então `sus-1` é Vitória Belmiro numa partida e Nazareno Cruz na
 * seguinte — retrato preso ao id faria a mesma cara aparecer como quatro
 * pessoas diferentes. O nome é o que identifica alguém.
 *
 * A lista é fechada de propósito: são dez suspeitos possíveis e uma vítima, e
 * qualquer partida do cenário atual sai daí. Cenário novo traz nomes novos, e
 * quem não estiver aqui cai nas iniciais em vez de num 404.
 */

const ELENCO = new Set([
  "aurelio-bastos",
  "bartolomeu-sa",
  "clarice-antunes",
  "godofredo-alves",
  "ilma-prado",
  "marlene-tostes",
  "nazareno-cruz",
  "ondina-vilar",
  "rodolfo-andrade",
  "teodoro-mainz",
  "vitoria-belmiro",
]);

// Faixa dos diacríticos combinantes, que `normalize("NFD")` separa das letras.
// Comparada por código em vez de escrita numa classe de regex: os caracteres
// dessa faixa são invisíveis no editor, e código que ninguém consegue ler é
// código que ninguém consegue revisar.
const ACENTO_INICIO = 0x300;
const ACENTO_FIM = 0x36f;

export function apelido(nome: string): string {
  const semAcento = [...nome.normalize("NFD")]
    .filter((letra) => {
      const codigo = letra.codePointAt(0) ?? 0;
      return codigo < ACENTO_INICIO || codigo > ACENTO_FIM;
    })
    .join("");

  return semAcento
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

export function retratoDe(nome: string): string | null {
  const slug = apelido(nome);
  return ELENCO.has(slug) ? `/retratos/${slug}.png` : null;
}

/** O que aparece quando não há retrato: as iniciais, e nada de erro na tela. */
export function iniciais(nome: string): string {
  return nome
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((parte) => parte[0]?.toUpperCase() ?? "")
    .join("");
}
