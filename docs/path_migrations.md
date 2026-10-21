# Documentation path migration

Documentation is consolidated under `docs/`. Existing filenames and the
`design/` and `hardening/` subdirectories remain intact.

| Previous repository path | Current repository path |
| --- | --- |
| `doc/<path>` | `docs/<path>` |
| `findings/<report>.md` | `docs/findings/<report>.md` |
| `findings/direct_stream_window_analysis.py` | `eval/scripts/direct_stream_window_analysis.py` |
| `note.txt` | `docs/archive/note.txt` |

The [findings index](findings/index.md) distinguishes research reports from
current qualification evidence. The [archived-note guide](archive/README.md)
explains the scratchpad's historical status. Runtime behavior, legacy tools,
dependency locks, generated reference-card bytes and personal agent state are
outside this documentation cleanup.

## Historical evidence

The [findings ledger](hardening/FINDINGS.yaml) is moved without modifying its
bytes. Existing artifact manifests, receipts, source commits, hashes, recorded
commands and qualification metadata retain their original identities. Literal
paths inside historical reports may therefore still use `doc/` or `findings/`.
Consult those files at their recorded source commit to interpret original line
numbers and exact bytes; the table above locates their current descendants.

The ledger validator recognizes both current documentation paths and these
relocated historical references. A reference still requires an existing target;
the existing raw-artifact archive policy is unchanged. Source, test and artifact
paths do not receive a documentation fallback.

The default SiteProfile's historical `evidence_refs` entry in
[site.py](../src/exaserve/site.py) deliberately retains its original `doc/` path:
that string is included in its canonical hash. The ADR now lives at
[docs/hardening/decisions/ADR-000-production-envelope.md](hardening/decisions/ADR-000-production-envelope.md).
The documentation move does not create a new qualified profile or transfer
historical hardware results to the current code.

## Generated reference card

The existing Word reference card is retained at its new documentation path.
Its generator reads figures from `docs/figures/`; those figures and the Academy
template remain externally supplied inputs described in
[the reference-card guide](exaserve.md#regenerating-the-word-reference-card).
The card is not regenerated as part of the directory migration.
