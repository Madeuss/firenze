"""Reading a model's bookkeeping in the vocabulary the house keeps.

The structured fields of a reply are ids: `parlour`, not "the parlour"; `2`, not
"22h00". The prompt says so and lists them (npc/v3). A model still misses, and
the two ways it misses are worth separating:

- **a blank where nothing belongs.** `claimed_room: ""` is not a claim about an
  empty-named room, it is the absence of a claim written the wrong way;
- **a sentinel where nothing belongs.** `claimed_interval: -1` is the same
  thing in a numeric field. The schema is sent in strict mode, which requires
  every property to be present, so "I am not saying where I was" has no shape
  to arrive in — and the model reaches for the oldest one there is. Measured on
  the real model: of 40 replies, 30 named a real hour, 4 wrote null, and 6 wrote
  `-1`. Not one wrote a clock time or an hour outside the night. Every single
  rejection of this kind was a reply making no claim at all;
- **the name instead of the id.** The character says "salão" out loud in the
  same breath, and writes it down where the id goes.

Both are normalised here, before the guard sees the reply. This is not the guard
going soft: what comes out is still an id or still wrong, and
`claim_is_about_this_case` still throws out anything that does not resolve. The
difference is that a player no longer loses a turn because a model wrote a word
the house can translate without guessing.

What is deliberately *not* done here is inventing a claim. A room with no hour
stays a room with no hour, and the guard discards it — the hour is what makes a
claim comparable to another claim, and picking one would be the house putting
words in a suspect's mouth (RN-021).
"""

import unicodedata

from firenze.domain import Case
from firenze.i18n import Catalog
from firenze.interrogation.models import NpcReply

VAZIOS = ("", "none", "null", "n/a", "nenhum", "nenhuma")


def _achatar(texto: str) -> str:
    """Sem acento, sem caixa, sem artigo solto na frente."""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    limpo = sem_acento.strip().lower()
    for artigo in ("o ", "a ", "os ", "as ", "no ", "na ", "the "):
        if limpo.startswith(artigo):
            limpo = limpo[len(artigo) :]
    return limpo.strip()


def _nada(valor: str | None) -> bool:
    return valor is None or _achatar(valor) in VAZIOS


def normalise(reply: NpcReply, case: Case, catalog: Catalog) -> NpcReply:
    """The same reply, with its ids written the way the house writes them."""
    mudancas: dict[str, object] = {}

    for campo in ("fact_referenced", "clue_revealed", "claimed_room"):
        if _nada(getattr(reply, campo)):
            mudancas[campo] = None

    # Negativo não é hora nenhuma desta noite, e não é engano de índice: é a
    # ausência de alegação escrita como número. Ler assim é o contrário de
    # inventar — inventar seria escolher uma hora que ninguém disse.
    if reply.claimed_interval is not None and reply.claimed_interval < 0:
        mudancas["claimed_interval"] = None

    quarto = mudancas.get("claimed_room", reply.claimed_room)
    if isinstance(quarto, str) and quarto not in case.rooms:
        # O nome de exibição identifica o cômodo sem ambiguidade neste idioma;
        # traduzir de volta não é adivinhar.
        por_nome = {_achatar(catalog.room(room)): room for room in case.rooms}
        achado = por_nome.get(_achatar(quarto))
        if achado is not None:
            mudancas["claimed_room"] = achado

    return reply.model_copy(update=mudancas) if mudancas else reply
