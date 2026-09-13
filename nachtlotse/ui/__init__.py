"""Swappable UI layer — streamlit today, possibly Qt or a web app later.

Imports `planning`, `engine`, and `data`, never the other way around (see
CLAUDE.md's dependency-direction rule). This package holds no planning
logic of its own; `nachtlotse.planning` is the single shared pipeline
every UI calls.
"""
