# Tests

**English:** [Testing](Testing)

```bash
uv run pytest                                  # alle Tests
uv run --extra charts --extra gui pytest       # mit PNG- und App-Tests
uv run ruff check .                            # Lint
uv run ruff format .                           # Formatierung
```

Es gibt über 400 Tests, sie laufen in etwa 20 Sekunden durch.

Die Astronomie wird gegen bekannte Werte aus unabhängigen Quellen getestet,
nicht gegen die eigenen Formeln des Codes: Kulminationshöhen, Polaris auf der
Höhe des Breitengrads, der parallaktische Winkel gegen die Lehrbuchformel,
Kometenpositionen gegen JPL Horizons, Himmelsabstände gegen astropy.

Die Tests gehen nie ins Internet. Jede Netzwerkquelle wird in
`tests/conftest.py` durch eine Attrappe ersetzt, und jeder Test bekommt einen
eigenen leeren Zwischenspeicher. Tests, die matplotlib oder PySide6
brauchen, überspringen sich selbst, wenn der Zusatz fehlt. Die App-Tests
laufen ohne sichtbares Fenster.

Jede neue Regel in der Engine kommt mit einem Test gegen einen bekannten
Wert.
