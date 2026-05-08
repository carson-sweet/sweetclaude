# Roadmap

SweetClaude is in active development. This roadmap reflects current direction, not a commitment. Things move; priorities shift.

---

## Now

Work that is actively in progress or nearly complete.

- **Demo terminal recording** — A 90-second recording showing `/sweetclaude:go` through a first product brief skeleton. Pending.
- **Co-maintainer search** — Actively looking. See [issue #7](https://github.com/carson-sweet/sweetclaude/issues/7).

---

## Next

Committed work that hasn't started yet.

- **Behavioral regression CI** — Automate the 15-contract behavioral test suite against a CI trigger tied to model version tags. Turns the manual process into published, model-version-tagged compliance reports. Significant engineering; the most differentiating capability on the roadmap.
- **Standalone `init` and `adopt` skills** — The v3 `setup` skill handles new and existing projects via auto-detection. `init` and `adopt` still exist as explicit alternatives. More distinct entry path UX may still be worth investing in.

---

## Later

On the backlog but not actively planned.

- **Full README reorganization** — README (pitch only) + INSTALL.md + QUICKSTART.md. The current README is good enough; the structural reorganization is a polish pass for when there's a second maintainer to coordinate it.
- **Security planning skill** — A dedicated skill for the security planning work type. Currently handled through `product-discovery` compliance context and `code-review`. A standalone skill would make the ASSESS → DEFINE → SHIP workflow more explicit.
- **Infrastructure change skill** — Dedicated workflow for the infrastructure change work type. High-blast-radius work that currently relies on the abbreviated pipeline.

---

## What This Is Not

This roadmap is not a release calendar. SweetClaude does not generate timelines. The items above are direction, not schedule. Each moves from Later → Next → Now when conditions are right.

If you want to work on anything in Next or Later, open an issue or comment on an existing one. Co-maintainer and contributor work on roadmap items is welcome.
