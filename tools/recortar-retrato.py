"""Tira o xadrez pintado de um JPG e salva PNG com alfa de verdade.

    uv run --with pillow --with numpy --with scipy         python tools/recortar-retrato.py entrada.jpg saida.png [tolerancia]

A ferramenta que gera os retratos exporta JPG com o xadrez de transparencia
*desenhado* na imagem. JPG nao tem canal alfa, entao nao ha o que extrair: o
fundo precisa ser reconhecido e recortado.

Duas decisoes, e a segunda so apareceu depois de tres tentativas erradas.

**As cores do xadrez sao aprendidas da linha do topo**, nao chutadas. Cada
imagem veio com um xadrez diferente — cinza neutro, caqui, oliva escuro, e num
caso duas tonalidades que diferem por dois niveis — e valor fixo erra sempre.

**Reconstrucao morfologica, em vez de tolerancia bem escolhida.** O modo como o
recorte estraga e sempre o mesmo: um trecho da roupa ou da pele tem quase a cor
do fundo, forma uma *ponte fina* com ele, e o preenchimento atravessa e come a
pessoa. Nao adianta escolher melhor a tolerancia — a ponte existe em qualquer
valor que remova o fundo inteiro; e nao adianta vigiar buraco fechado, porque a
mordida continua ligada a borda.

Entao: erode a mascara ate as pontes finas se romperem, guarda so o que sobrou
grudado na borda, e daí *reconstroi* esse nucleo de volta dentro da mascara
original. O fundo volta inteiro ate a silhueta; a mordida nao volta, porque o
nucleo dela morreu na erosao.
"""

import sys

import numpy as np
from PIL import Image
from scipy import ndimage

EROSAO = 3  # espessura da ponte que ainda conta como vazamento


TOLERANCIAS = (26, 22, 18, 14, 11, 8)
SOBRA_MINIMA = 0.30
"""Fracao da imagem que a pessoa tem que ocupar depois do recorte.

E o que separa recorte bom de mordida, e sai da medicao: nos que sairam certos
sobraram de 47% a 64%; nos comidos, de 8% a 22%. Retrato de busto nunca ocupa
menos que isso, entao tolerancia que deixa a pessoa pequena vazou para dentro
dela."""


def _separar(a: np.ndarray, dominantes: np.ndarray, tolerancia: int) -> np.ndarray:
    parecido = np.zeros(a.shape[:2], dtype=bool)
    for cor in dominantes:
        parecido |= np.all(np.abs(a - cor) <= tolerancia, axis=2)

    # Nucleo: o que continua ligado a borda depois de romper as pontes finas.
    # border_value=1: sem isso a erosao apaga a propria borda da imagem e nao
    # sobra rotulo nenhum para semear o nucleo.
    magro = ndimage.binary_erosion(parecido, iterations=EROSAO, border_value=1)
    rotulos, _ = ndimage.label(magro)
    borda = np.concatenate([rotulos[0, :], rotulos[-1, :], rotulos[:, 0], rotulos[:, -1]])
    nucleo = np.isin(rotulos, np.unique(borda[borda > 0]))

    # E o fundo volta a crescer, mas so dentro do que ja parecia fundo.
    fundo = ndimage.binary_propagation(nucleo, mask=parecido)

    quase = np.zeros(a.shape[:2], dtype=bool)
    for cor in dominantes:
        quase |= np.all(np.abs(a - cor) <= int(tolerancia * 1.6), axis=2)
    for _ in range(EROSAO + 1):
        fundo |= ndimage.binary_dilation(fundo) & quase
    return ~ndimage.binary_fill_holes(~fundo)


def _sobra(fundo: np.ndarray) -> float:
    """Tamanho do maior pedaco continuo que sobrou — a pessoa."""
    rotulos, quantos = ndimage.label(~fundo)
    if not quantos:
        return 0.0
    return max(np.bincount(rotulos.ravel())[1:]) / fundo.size


def recortar(origem: str, destino: str, forcada: int = 0) -> tuple[tuple[int, int], int, int]:
    im = Image.open(origem).convert("RGB")
    a = np.asarray(im).astype(np.int16)

    topo = a[0].reshape(-1, 3)
    cores, contagem = np.unique(topo // 6, axis=0, return_counts=True)
    dominantes = cores[contagem >= topo.shape[0] * 0.04] * 6 + 3

    candidatas = (forcada,) if forcada else TOLERANCIAS
    for tolerancia in candidatas:
        fundo = _separar(a, dominantes, tolerancia)
        if _sobra(fundo) >= SOBRA_MINIMA:
            break
    else:
        raise SystemExit(f"{origem}: nao consegui separar o fundo sem comer a pessoa")

    rgba = np.dstack([np.asarray(im), np.where(fundo, 0, 255).astype(np.uint8)])
    saida = Image.fromarray(rgba, "RGBA")
    saida = saida.crop(saida.split()[3].getbbox())
    saida.save(destino)
    return saida.size, int(fundo.sum() * 100 / fundo.size), tolerancia


if __name__ == "__main__":
    tamanho, pct, tol = recortar(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 0)
    print(f"{sys.argv[2]}: {tamanho[0]}x{tamanho[1]}, {pct}% removido (tolerancia {tol})")
