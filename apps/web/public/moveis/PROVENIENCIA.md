# De onde vêm estes modelos

Dez peças do **Ultimate House Interior Pack**, de [Quaternius](https://quaternius.com),
em **CC0** — domínio público, sem exigência de atribuição, uso comercial
liberado. Baixados de [Poly Pizza](https://poly.pizza/bundle/Ultimate-House-Interior-Pack-2SXnFbwFzm).

O crédito está aqui porque a licença não exigir não é motivo para não dizer de
onde veio uma coisa.

| Arquivo | Modelo no pacote |
|---|---|
| `mesa.glb` | Table Round Large |
| `mesa-pequena.glb` | Table Round Small |
| `cadeira.glb` | Chair |
| `estante.glb` | Shelf Large |
| `poltrona.glb` | Couch Small |
| `vaso.glb` | Houseplant |
| `fogao.glb` | Oven |
| `bancada.glb` | Kitchen Sink |
| `comoda.glb` | Drawer |
| `lareira.glb` | Fireplace |

**Barril e caixote não vêm daqui.** O pacote não os tem, e adega sem barril não
é adega — os dois continuam desenhados com primitivas em `Moveis.tsx`.

Os modelos não são usados como vieram: cada um tem a própria escala e o próprio
centro, então a caixa envolvente é medida no carregamento e a peça é encaixada
no vulto que `mobilia.ts` reserva para a espécie. É isso que garante que nada
atravesse parede.
