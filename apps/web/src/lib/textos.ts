/**
 * O que a moldura do jogo diz, em cada idioma.
 *
 * A divisão é a mesma que a API já faz (ADR-0005): **o conteúdo do caso vem
 * pronto do servidor** — fatos, cômodos, motivos, falas dos suspeitos, a função
 * de cada um — no idioma da partida. O que está aqui é só a moldura: botões,
 * rótulos, instruções. Nada de mistério, nada de prosa do caso.
 *
 * Um dicionário tipado e não uma biblioteca de i18n por dois motivos. O
 * primeiro é que o TypeScript já faz o trabalho que interessa: `Textos` é
 * derivado do português, então esquecer uma chave no inglês não compila — que
 * é a falha que o gettext deixa passar até o texto aparecer cru na tela. O
 * segundo é que as bibliotecas boas do ecossistema pedem Babel, e adotar Babel
 * no Next 16 desliga o Turbopack do projeto inteiro em troca de traduzir umas
 * oitenta frases.
 *
 * Nomes próprios não entram aqui. Uma mansão brasileira mantém nomes
 * brasileiros em qualquer idioma; traduzir soaria a dublagem ruim.
 */

export type Locale = 'pt-BR' | 'en'

export const IDIOMAS: readonly { id: Locale; nome: string }[] = [
  { id: 'pt-BR', nome: 'Português' },
  { id: 'en', nome: 'English' },
]

const PT = {
  // início
  'inicio.semente': 'semente',
  'inicio.semente.pergunta': 'o que é a semente',
  'inicio.semente.qualquer': 'qualquer',
  'inicio.semente.rotulo': 'semente do caso, opcional',
  'inicio.semente.texto':
    'O mesmo número gera sempre o mesmo mistério — mesmo elenco, mesmo culpado, mesma noite. Serve para repetir um caso, ou passar um bom para alguém. Em branco, você recebe uma noite qualquer.',
  'inicio.idioma': 'idioma',
  'inicio.idioma.rotulo': 'idioma da partida',
  'inicio.idioma.aviso': 'vale para a partida inteira, e não muda depois',
  'inicio.comecar': 'Começar investigação',
  'inicio.abrindo': 'abrindo a casa…',
  'inicio.falha': 'não deu para começar',

  // regras
  'regras.titulo': 'Como se joga',
  'regras.como': 'como se joga',
  'regras.entendi': 'Entendi',
  'regras.pitch':
    'Um homem foi encontrado morto na própria casa. Seis pessoas estavam lá, e todas têm o que esconder — só uma esconde o assassinato.',
  'regras.turnos': 'Trinta turnos para perguntar. Cada pergunta gasta um.',
  'regras.confronto':
    'Confrontar alguém com uma prova custa dois, e só vale com prova que você tem.',
  'regras.pensar':
    'Pensar não custa nada. Trocar de suspeito e reler o caderno são de graça.',
  'regras.acusacao': 'Uma acusação por partida, e ela não volta atrás.',

  // interrogatório
  'jogo.caso': 'Caso',
  'jogo.turnos': 'turnos',
  'jogo.interrogatorio': 'Interrogatório',
  'jogo.deducao': 'Dedução',
  'jogo.deducao.gratis': 'não gasta turno',
  'jogo.acusar': 'Acusar',
  'jogo.elenco': 'elenco',
  'jogo.mudo': 'ainda não falou com você',
  'jogo.silencio.nada': 'Ninguém disse nada ainda. Pergunte alguma coisa.',
  'jogo.silencio.turno': 'Não veio resposta. O turno foi gasto.',
  'jogo.voce': 'você',
  'jogo.apresentar': 'apresentar',
  'jogo.cancelar': 'cancelar',
  'jogo.pergunte': 'pergunte alguma coisa…',
  'jogo.pergunta.rotulo': 'sua pergunta',
  'jogo.perguntar': 'Perguntar',
  'jogo.confrontar': 'Confrontar — custa 2 turnos',
  'jogo.provas': 'provas',
  'jogo.provas.vazio': '— nada nas mãos ainda',
  'jogo.sem.turnos': 'Turnos insuficientes. Só resta acusar.',
  'jogo.falha.pergunta': 'não deu para perguntar',
  'jogo.falha.partida': 'não deu para abrir a partida',
  'jogo.custo':
    'perguntar gasta 1 turno, confrontar gasta 2 · o painel ao lado não gasta nada',
  'postura.cooperative': 'cooperativo',
  'postura.evasive': 'evasivo',
  'postura.hostile': 'hostil',
  'postura.broken': 'quebrado',

  // dedução
  'deducao.planta': 'Planta',
  'deducao.grade': 'Grade',
  'deducao.hora': 'hora da noite',
  'deducao.hora.crime': 'por volta desta hora o corpo foi encontrado',
  'deducao.corpo': 'onde o corpo foi encontrado',
  'deducao.bandeja': 'suspeitos sem lugar nesta hora',
  'deducao.bandeja.vazia': 'todos colocados nesta hora',
  'deducao.onde': 'onde {nome} disse que estava?',
  'deducao.solte':
    'Solte {nome} num cômodo — ou fora da planta, para tirá-la de lá.',
  'deducao.instrucao':
    'Arraste um retrato para um cômodo, e de um cômodo para outro. Isto é seu caderno — nada aqui vem do jogo.',
  'deducao.celula.vazia': 'sem anotação',

  // seletor de cômodo
  'comodo.dialogo': 'onde ele disse que estava',
  'comodo.filtro': 'cômodo…',
  'comodo.filtro.rotulo': 'filtrar cômodos',
  'comodo.nenhum': 'nenhum cômodo com esse nome',
  'comodo.apagar': 'apagar esta anotação',

  // acusação
  'acusacao.dialogo': 'acusação',
  'acusacao.quem': 'Quem foi?',
  'acusacao.dica':
    'Escreva com suas palavras — quem, por quê, e com que prova. Você confere antes de valer.',
  'acusacao.exemplo':
    'foi a governanta, por causa da herança, e a prova é o lenço…',
  'acusacao.rotulo': 'sua acusação, em texto livre',
  'acusacao.voltar': 'voltar',
  'acusacao.escolher': 'prefiro escolher',
  'acusacao.lendo': 'lendo…',
  'acusacao.continuar': 'Continuar',
  'acusacao.confira': 'Confira antes de valer',
  'acusacao.culpado': 'culpado',
  'acusacao.motivo': 'motivo',
  'acusacao.provas': 'provas',
  'acusacao.ninguem': '— ninguém',
  'acusacao.motivo.nenhum': '— você não descobriu nenhum',
  'acusacao.motivo.livre': '— não reivindicado',
  'acusacao.sobrou':
    'Não consegui encaixar: {itens}. Ajuste acima — não vou adivinhar por você.',
  'acusacao.irreversivel': 'Isto não pode ser desfeito.',
  'acusacao.acusando': 'acusando…',
  'acusacao.acusar': 'Acusar',
  'acusacao.falha.leitura': 'não deu para ler a acusação',
  'acusacao.falha.acusar': 'não deu para acusar',

  // veredito
  'veredito.certo': 'Era ele mesmo.',
  'veredito.errado': 'Não era.',
  'veredito.frase': 'Foi {culpado}, com {meio}, por {motivo}.',
  'veredito.culpado': 'culpado',
  'veredito.motivo': 'motivo',
  'veredito.provas': 'provas',
  'veredito.rapidez': 'rapidez',
  'veredito.total': 'total',
  'veredito.nova': 'Nova investigação',
} as const

export type Chave = keyof typeof PT
export type Textos = Record<Chave, string>

/** O inglês é tipado pelo português: chave faltando não compila. */
const EN: Textos = {
  'inicio.semente': 'seed',
  'inicio.semente.pergunta': 'what the seed is',
  'inicio.semente.qualquer': 'any',
  'inicio.semente.rotulo': 'case seed, optional',
  'inicio.semente.texto':
    'The same number always builds the same mystery — same cast, same culprit, same night. Use it to replay a case, or to pass a good one on. Leave it empty and you get whatever night comes up.',
  'inicio.idioma': 'language',
  'inicio.idioma.rotulo': 'language of the match',
  'inicio.idioma.aviso': 'it holds for the whole match, and cannot be changed later',
  'inicio.comecar': 'Begin the investigation',
  'inicio.abrindo': 'opening the house…',
  'inicio.falha': 'could not start',

  'regras.titulo': 'How to play',
  'regras.como': 'how to play',
  'regras.entendi': 'Got it',
  'regras.pitch':
    'A man was found dead in his own house. Six people were there, and every one of them has something to hide — only one is hiding the murder.',
  'regras.turnos': 'Thirty turns to ask questions. Each question spends one.',
  'regras.confronto':
    'Confronting someone with evidence costs two, and only counts with evidence you hold.',
  'regras.pensar':
    'Thinking costs nothing. Switching suspects and rereading the notebook are free.',
  'regras.acusacao': 'One accusation per match, and it does not come back.',

  'jogo.caso': 'Case',
  'jogo.turnos': 'turns',
  'jogo.interrogatorio': 'Interrogation',
  'jogo.deducao': 'Deduction',
  'jogo.deducao.gratis': 'costs no turn',
  'jogo.acusar': 'Accuse',
  'jogo.elenco': 'cast',
  'jogo.mudo': 'has not spoken to you yet',
  'jogo.silencio.nada': 'Nobody has said anything yet. Ask them something.',
  'jogo.silencio.turno': 'No answer came. The turn was spent.',
  'jogo.voce': 'you',
  'jogo.apresentar': 'present',
  'jogo.cancelar': 'cancel',
  'jogo.pergunte': 'ask them something…',
  'jogo.pergunta.rotulo': 'your question',
  'jogo.perguntar': 'Ask',
  'jogo.confrontar': 'Confront — costs 2 turns',
  'jogo.provas': 'evidence',
  'jogo.provas.vazio': '— nothing in hand yet',
  'jogo.sem.turnos': 'Not enough turns. All that is left is to accuse.',
  'jogo.falha.pergunta': 'could not ask',
  'jogo.falha.partida': 'could not open the match',
  'jogo.custo':
    'asking spends 1 turn, confronting spends 2 · the panel beside costs nothing',
  'postura.cooperative': 'cooperative',
  'postura.evasive': 'evasive',
  'postura.hostile': 'hostile',
  'postura.broken': 'broken',

  'deducao.planta': 'Plan',
  'deducao.grade': 'Grid',
  'deducao.hora': 'hour of the night',
  'deducao.hora.crime': 'around this hour the body was found',
  'deducao.corpo': 'where the body was found',
  'deducao.bandeja': 'suspects with no room this hour',
  'deducao.bandeja.vazia': 'everyone placed this hour',
  'deducao.onde': 'where did {nome} say they were?',
  'deducao.solte':
    'Drop {nome} in a room — or off the plan, to take them out of it.',
  'deducao.instrucao':
    'Drag a portrait into a room, and from one room to another. This is your notebook — nothing here comes from the game.',
  'deducao.celula.vazia': 'no note',

  'comodo.dialogo': 'where they said they were',
  'comodo.filtro': 'room…',
  'comodo.filtro.rotulo': 'filter rooms',
  'comodo.nenhum': 'no room by that name',
  'comodo.apagar': 'erase this note',

  'acusacao.dialogo': 'accusation',
  'acusacao.quem': 'Who did it?',
  'acusacao.dica':
    'Write it in your own words — who, why, and with what evidence. You get to check it before it counts.',
  'acusacao.exemplo':
    'it was the housekeeper, over the inheritance, and the proof is the handkerchief…',
  'acusacao.rotulo': 'your accusation, in free text',
  'acusacao.voltar': 'back',
  'acusacao.escolher': 'I would rather pick',
  'acusacao.lendo': 'reading…',
  'acusacao.continuar': 'Continue',
  'acusacao.confira': 'Check it before it counts',
  'acusacao.culpado': 'culprit',
  'acusacao.motivo': 'motive',
  'acusacao.provas': 'evidence',
  'acusacao.ninguem': '— nobody',
  'acusacao.motivo.nenhum': '— you found none',
  'acusacao.motivo.livre': '— unclaimed',
  'acusacao.sobrou':
    'I could not place: {itens}. Fix it above — I will not guess for you.',
  'acusacao.irreversivel': 'This cannot be undone.',
  'acusacao.acusando': 'accusing…',
  'acusacao.acusar': 'Accuse',
  'acusacao.falha.leitura': 'could not read the accusation',
  'acusacao.falha.acusar': 'could not accuse',

  'veredito.certo': 'It was him after all.',
  'veredito.errado': 'It was not.',
  'veredito.frase': 'It was {culpado}, with {meio}, over {motivo}.',
  'veredito.culpado': 'culprit',
  'veredito.motivo': 'motive',
  'veredito.provas': 'evidence',
  'veredito.rapidez': 'speed',
  'veredito.total': 'total',
  'veredito.nova': 'New investigation',
}

const CATALOGOS: Record<Locale, Textos> = { 'pt-BR': PT, en: EN }

/** Locale desconhecido cai no português, que é o idioma padrão da partida. */
export function textos(locale: string): Textos {
  return CATALOGOS[locale as Locale] ?? PT
}

/** Preenche `{slots}` de uma frase. O catálogo guarda a frase inteira, e não
 * pedaços concatenados, porque a ordem das palavras é do idioma. */
export function com(frase: string, slots: Record<string, string>): string {
  return frase.replace(/\{(\w+)\}/g, (cru, chave: string) => slots[chave] ?? cru)
}
