# Favoriten

**English:** [Favorites](Favorites)

Favoriten sind Objekte, die du immer auf deiner Liste haben willst, egal wie
sie abschneiden. T CrB ist das typische Beispiel: eine wiederkehrende Nova,
die zwischen den Ausbrüchen jahrzehntelang bei etwa 10 mag liegt und es nie
in eine normale Top Five schaffen würde.

```bash
cp nachtlotse/data/favorites_local.template.yaml nachtlotse/data/favorites_local.yaml
```

Die Datei ist eine Liste von Katalognummern, genau so geschrieben wie in
`nachtlotse/data/catalog/*.yaml`. Namen und Aliase funktionieren hier nicht.

```yaml
- "T CrB"
- "M31"
```

Ein Favorit wird immer geprüft, auch jenseits von `--limit` (EVALUATE in der
App). Wenn er in der Nacht sichtbar ist, kommt er hinter den ersten fünf auf
die Liste. Er verdrängt kein anderes Ziel und rückt auch nicht vor sie.
Favoriten sind in den Tabellen mit ★ markiert und auf der
[Himmelskarte](Himmelskarte-und-Export) als Stern gezeichnet.

Fehlt ein Favorit in einem Plan, ist er in dieser Nacht nicht sichtbar. Wie
Standorte und Ausrüstung ignoriert git auch die Favoritendatei.
