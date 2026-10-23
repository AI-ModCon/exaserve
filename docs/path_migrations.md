# Documentation path migration

Documentation is consolidated under `docs/`. Existing filenames and the
`design/` and `hardening/` subdirectories remain intact.

| Previous repository path | Current repository path |
| --- | --- |
| `doc/<path>` | `docs/<path>` |
| `findings/<report>.md`, later `docs/findings/<report>.md` | Removed from the current tree; summarized in the [operations handbook](operations_handbook.md) |
| `findings/direct_stream_window_analysis.py` | `eval/scripts/direct_stream_window_analysis.py` |
| Run logs, audits and campaign records under `docs/`, `docs/hardening/` and the paper suite's spec folder | Removed from the current tree; summarized in the [operations handbook](operations_handbook.md) |
| `note.txt` | Removed from the published tree (personal development scratchpad) |

Runtime behavior, legacy tools, dependency locks, generated reference-card bytes
and personal agent state are outside this documentation cleanup.

## Historical evidence

The initial move of the [findings ledger](hardening/FINDINGS.yaml) preserved its
bytes. The later retirement of run records updates baseline, affected-region
and evidence references in the current ledger; recorded finding statuses,
decisions and artifact hashes retain their original values. Existing artifact
manifests, receipts, source commits, recorded commands and qualification
metadata retain their original identities, so paths they cite may still use
`doc/` or `findings/`. Consult cited files at their
recorded source commit to interpret original line numbers and exact bytes; the
table above locates their current descendants, and removed records remain in the
repository history.

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

The current tree carries no maintainer account paths, compute-node names,
allocation-internal addresses, reservation or job identifiers, or run
narratives. A maintainer's home or project directory appears as
`/home/YOUR_USER/...` or `/lus/flare/projects/YOUR_PROJECT/YOUR_USER/...`; test
fixtures use synthetic node labels such as `node-10-4-1` and documentation
addresses from `192.0.2.0/24`. Run logs, audits and campaign records that
carried such details were removed (see the table above); their lessons are in
the [operations handbook](operations_handbook.md). Maintainer helpers appear
generically: the site environment script
(`EXASERVE_ENV_SCRIPT_AURORA`), allocation leases (recorded in qualification
evidence as `acquisition_source: subjob`, with the `AURORA_SUBJOB` session
marker) and the interactive-allocation fallback. The allocation
name is absent from the current tree, and the code has no default PBS account or project root
([getting started](getting_started.md#configure-evaluation-environment-preparation)).

The legacy paper-evidence ledger
([pp405b_legacy_evidence.yaml](../eval/plot/pp405b_legacy_evidence.yaml),
schema 3) no longer stores job identifiers. In each run cell its loader selects
the retained PBS stdout file whose bytes match the pinned SHA-256 (a cell can
keep several from resubmissions) and reads the job identifier and server from
that file's name. Measurements and pinned evidence hashes are unchanged. Ledger
reference updates are described above; the original text remains at each
record's source commit.
This redaction applies to the current tree; Git history is not rewritten
([disclosure decision](modcon_compliance.md#operational-details-kept-for-the-disclosure-decision)).

## Retired branches

The repository is published with `main` only. Every other development branch
and the tags `v0.1.0`, `v0.2.0` and `v0.4.0-rc2` were audited and are removed
before the visibility change: their code is part of `main`'s history, or they
held an abandoned prototype or a cleanup that was not merged. Summaries of the
recurring issues found during the audit are in
[known issues](KNOWN_ISSUES.md#lessons-kept-from-retired-branches).

## Generated reference card

The Word reference card is retained at its new documentation path.
Its generator reads figures from `docs/figures/`; those figures and the Academy
template remain externally supplied inputs described in
[the reference-card guide](exaserve.md#regenerating-the-word-reference-card).
The card was regenerated for publication with the `AI-ModCon/exaserve` URL,
synthetic example identifiers and the current `docs/` paths.
