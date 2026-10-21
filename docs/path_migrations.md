# Documentation path migration

Documentation is consolidated under `docs/`. Existing filenames and the
`design/` and `hardening/` subdirectories remain intact.

| Previous repository path | Current repository path |
| --- | --- |
| `doc/<path>` | `docs/<path>` |
| `findings/<report>.md` | `docs/findings/<report>.md` |
| `findings/direct_stream_window_analysis.py` | `eval/scripts/direct_stream_window_analysis.py` |
| `note.txt` | Removed from the published tree (personal development scratchpad) |

The [findings index](findings/index.md) distinguishes research reports from
current qualification evidence. Runtime behavior, legacy tools,
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

### Publication redaction

Before the repository was opened, operational details were redacted from
documentation, example and hardening configurations, frozen evaluation specs
and test fixtures. A maintainer's home or project directory appears as
`/home/YOUR_USER/...` or `/lus/flare/projects/YOUR_PROJECT/YOUR_USER/...`.
Compute-node names keep their Aurora format but use synthetic racks
`x9001` to `x9025`; one real rack maps to one synthetic rack, so statements
about shared racks still hold. Allocation-internal addresses appear as
documentation addresses from `192.0.2.0/24`, and a reservation identifier as
`<reservation>`. PBS job identifiers appear as labels `J001` to `J095`,
numbered in job order; a job keeps its label in every document. The allocation
name is not published, and the code has no default PBS account or project root
([getting started](getting_started.md#configure-evaluation-environment-preparation)).

The legacy paper-evidence ledger
([pp405b_legacy_evidence.yaml](../eval/plot/pp405b_legacy_evidence.yaml),
schema 3) no longer stores job identifiers. In each run cell its loader selects
the retained PBS stdout file whose bytes match the pinned SHA-256 (a cell can
keep several from resubmissions) and reads the job identifier and server from
that file's name. Measurements, evidence hashes and the findings ledger bytes
are unchanged. The original text remains at each record's source commit.

## Generated reference card

The Word reference card is retained at its new documentation path.
Its generator reads figures from `docs/figures/`; those figures and the Academy
template remain externally supplied inputs described in
[the reference-card guide](exaserve.md#regenerating-the-word-reference-card).
The card was regenerated for publication with the `AI-ModCon/exaserve` URL,
synthetic example identifiers and the current `docs/` paths.
