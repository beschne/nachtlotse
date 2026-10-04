**Deutsch:** [Favoriten](Favoriten)

Favorites are objects you always want on your list, no matter how they
score. T CrB is the classic case: a recurring nova that sits at 10th
magnitude for decades between outbursts and would never make it into a
normal top five.

```bash
cp nachtlotse/data/favorites_local.template.yaml nachtlotse/data/favorites_local.yaml
```

The file is a list of catalog IDs, written exactly as in
`nachtlotse/data/catalog/*.yaml`. Names and aliases don't work here.

```yaml
- "T CrB"
- "M31"
```

A favorite is always checked, even beyond `--limit` (EVALUATE in the app).
If it's up that night, it's added to the list after the top five. It never
pushes another target out and never moves above them. Favorites are marked
with ★ in the tables and drawn as a star on the [sky chart](Sky-Chart-and-Exports).

If a favorite is missing from a plan, it isn't up that night. Like your
sites and rigs, the favorites file is ignored by git.
