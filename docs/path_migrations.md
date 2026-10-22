# Documentation path migration

Documentation is consolidated under `docs/`. Existing filenames and the
`design/` and `hardening/` subdirectories remain intact.

| Previous repository path | Current repository path |
| --- | --- |
| `doc/<path>` | `docs/<path>` |
| `findings/<report>.md`, later `docs/findings/<report>.md` | Removed from the current tree; summarized in the [operations handbook](operations_handbook.md) |
| `findings/direct_stream_window_analysis.py` | `eval/scripts/direct_stream_window_analysis.py` |
| Run logs, audits and campaign records under `docs/`, `docs/hardening/` and `eval/specs/sc26workshop/` | Removed from the current tree; summarized in the [operations handbook](operations_handbook.md) |
| `note.txt` | Removed from the published tree (personal development scratchpad) |

Runtime behavior, legacy tools, dependency locks, generated reference-card bytes
and personal agent state are outside this documentation cleanup.

## Historical evidence

The [findings ledger](hardening/FINDINGS.yaml) is moved without modifying its
bytes. Existing artifact manifests, receipts, source commits, hashes, recorded
commands and qualification metadata retain their original identities, so paths
they cite may still use `doc/` or `findings/`. Consult cited files at their
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
that file's name. Measurements, evidence hashes and the findings ledger bytes
are unchanged. The original text remains at each record's source commit.
This redaction applies to the current tree; Git history is not rewritten
([disclosure decision](modcon_compliance.md#operational-details-kept-for-the-disclosure-decision)).

## Retired branches

The repository is published with `main` only: the 15 branches below, audited on
2026-10-21, and the tags `v0.1.0`, `v0.2.0` and `v0.4.0-rc2` are removed before
the visibility change. Historical records may still name these branches.
Concise summaries of recurring issues found during the branch audit are in
[known issues](KNOWN_ISSUES.md#lessons-kept-from-retired-branches).

| Branch | Final commit | Relation to `main` |
| --- | --- | --- |
| `develop`, `release-v0.4.0`, `feature/slurm-amd-support`, `refactor/exaserve-rename`, `refactor/pluggable-interfaces` | `1158f26` | In `main`'s history |
| `paper/missing-scale-v0.4.0` | `044d3ef` | In `main`'s history |
| `null-compute` | `ea10c5d` | In `main`'s history |
| `perf-inst-stable` | `7ca4eee` | In `main`'s history |
| `serve-single-application` | `afb0349` | In `main`'s history |
| `feature/modcon-single-application-20261020` | `67253ad` | In `main`'s history |
| `docs/consolidation-20261020` | `d41efd1` | Merged as pull request #1 |
| `perf-inst` | `47865b4` | Every commit was reapplied to `main` in May 2026 |
| `archive/pre-release-dirty-20260830` | `a12ccf5` | A preview worktree snapshot whose code reached `main`; its specs differed from `main`'s only by run count and a 300 s reconnect grace |
| `release` | `c5a6b43` | A file-removal cleanup for a handoff; not merged |
| `openai-compat` | `546e0de` | An early prototype on Ray Serve's `build_openai_app`; abandoned |

## Generated reference card

The Word reference card is retained at its new documentation path.
Its generator reads figures from `docs/figures/`; those figures and the Academy
template remain externally supplied inputs described in
[the reference-card guide](exaserve.md#regenerating-the-word-reference-card).
The card was regenerated for publication with the `AI-ModCon/exaserve` URL,
synthetic example identifiers and the current `docs/` paths.
