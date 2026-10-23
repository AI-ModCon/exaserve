# Changelog

This records project changes and the verification scope of individual updates.
ExaServe's scale evaluations reached 256 Aurora nodes on earlier snapshots of
this code; smaller checks for a particular fix do not redefine the system's
demonstrated scale, and neither qualifies the current tree. Formal release
admission is tracked in [`docs/hardening/STATUS.md`](docs/hardening/STATUS.md).

## Unreleased

### Scale descriptions and reference card

- Describe ExaServe's demonstrated 1–256-node Aurora scale, measured on earlier
  snapshots of this code, in the overview, reference card and scale matrix.
  Keep fix-specific test coverage separate from system capability and
  packaged-release admission, and keep the verdict that no artifact is
  production-qualified.
- Refresh the generated Word reference card: the dense single-model Serve
  layout, the public arXiv citation and the operator-provisioned runtime setup
  replace stale descriptions, and the figures quoted from the paper are
  corrected. Refresh the scale and run sections of its Markdown companion.
- Document the reference updates to `docs/hardening/FINDINGS.yaml` when run
  records were retired; historical finding statuses, decisions and artifact
  hashes retain their recorded values.

### Validation coverage

The 256-node evaluations, made on earlier snapshots of this code, are
documented in the [paper](https://arxiv.org/abs/2609.10812) and
[operations handbook](docs/operations_handbook.md). Later regression checks
record the coverage of individual changes; their node counts are not a new
maximum for ExaServe.

- The implementation snapshot committed as "Cite the paper on arXiv and
  gather the plotting scripts" passed the seven portable CI-equivalent
  checks on an Aurora compute node. Fixed-order, randomized-order and
  installed-wheel suites each reported **1,771 passed, 40 skipped**. These are
  code/package regression results, not a rerun of the scale study. The later
  commits on this branch are covered by the pull request's CI run.
- Focused one-/two-node hardware and regression checks cover particular
  staging, control-plane and pipeline-parallel paths. Their scope stays with
  those checks rather than becoming a system-wide scale restriction.
- Earlier packaged candidate `final43` passed one- and two-node null/real XPU,
  PP=2 and failure-handling cells in validation mode. Its wheel SHA-256 is
  `1041be53eb5b5875d198d5ee6c6664718b4085775dcba99107873dd3d1fcdff2`.
  The successor `release-v0.4.0-rc2` passed a clean package gate; its wheel
  SHA-256 is
  `75bab1c97948d29237000d5fa087f3ed1f1d18e5ef3233fe2c759b4faf0e32f8`.
  These receipts remain tied to those artifacts.
- The default `SiteProfile`'s production-admission envelope records
  `supported_max_nodes=2`, `qualification_target_nodes=64` and
  `qualification_target_approved=false`, and the compiler enforces it:
  non-validation plans above two nodes fail, and validation-mode plans in that
  envelope stop at 64 nodes. These are admission limits, not the measured scale
  of the framework; this documentation update does not change them.

### Defect fixes

- The `paper` SLO preset of `eval.plot.goodput` and the preview figures'
  combined attainment use TTFT ≤ 2 s, the bound the paper and the full-sweep
  figures use; they used 1 s.
- HAProxy no longer runs on one thread when `gateway.worker_count` is 1 (the
  value in the examples); a count above 1 or `gateway.options.nbthread` still
  sets the thread count.
- Eval specs: an omitted `client.num_nodes` stays derived through YAML loading
  and matrix expansion (at most four client nodes for proxy runs, one per node
  for direct runs), and an explicit value is no longer overwritten by matrix
  expansion. Four start-up-only specs now get the one client node they set.
- Pipeline-parallel layer-name fallbacks stop the engine in production plans
  and print a warning in validation plans (`EXASERVE_VLLM_PP_LAYER_FALLBACK`).
- Plans of 16 or more nodes default to a 300 s control reconnect grace, which
  changes their deployment plan hash.
- Status writes (`StatusStore.transition` and `update`) require the
  `expected_revision` the writer read.
- `submit` and `submit-all` refuse a walltime above the one-hour debug and
  debug-scaling limit before contacting the scheduler. The 405B
  characterization spec asks for two hours below 256 nodes, so its 17-255-node
  cells run only as allocation-campaign children.
- Batch jobs no longer fail on ExaServe's own configuration variables. Since
  the built-in project root was removed, an eval job either failed at launch
  without `EXASERVE_PROJECT_ROOT` or, with it, was refused because the value
  names shared storage. The eval launcher now reads no site configuration and
  passes none to the serving process or the replay client, and the serving
  runtime drops
  `EXASERVE_PROJECT_ROOT`, `EXASERVE_MODEL_STORAGE_PATH`,
  `EXASERVE_LOCAL_STAGE_PATH` and `EXASERVE_ENV_SCRIPT_AURORA` from child
  environments.
- Import MPI only through `exaserve.mpi_loader`, which loads the interpreter's
  own libssl first: on Aurora's current image, source staging and the replay
  engine failed to import mpi4py once `hashlib` had loaded the stack's
  libcrypto.
- Correct the documented descriptor limit: Aurora compute nodes allow
  1,048,575 open files (16,384 is the login-node limit). `maxconn: 8000` stays
  as a conservative default.

### Publication readiness

- Name `AI-ModCon/exaserve` in package metadata, documentation and contribution
  links, and record the transfer in the AI-ModCon checklist.
- Redact maintainer account paths, compute-node names, allocation-internal
  addresses and a reservation identifier from documentation, example and
  hardening configurations, frozen evaluation specs and test fixtures; remove
  the personal development scratchpad; regenerate the reference card.
- Refresh the portable development lock with uv 0.13.4 and fixed releases of
  Pillow, pytest, Pygments, fontTools, certifi, aiohttp, virtualenv and
  OpenTelemetry. The lock now resolves Python 3.11–3.13. Declared server-extra
  and site runtime pins are unchanged; remaining dependency advisories are
  dispositioned in the AI-ModCon checklist.
- Name the paper's evaluation suite after its arXiv submission: specs live under
  `eval/specs/arxiv-submission/`, the figure scripts are
  `eval/plot/arxiv_submission_full_figures.py` and
  `eval/plot/arxiv_submission_preview.py`, and run groups resolve under
  `runs/arxiv-submission/`. A run group's `run.yaml` binds the absolute path it
  was written to, so groups recorded under another folder cannot be moved or
  renamed; set `EXASERVE_PAPER_SUITE_ROOT` to that folder to read them in place.
- Name GitHub's private vulnerability reporting in `SECURITY.md` beside the
  e-mail route. Document that the HAProxy build helper's 3.1.6 default is end of
  life and affected by CVE-2025-32464, and that the Pingora benchmark's declared
  0.5 range has published advisories.
- The reference card regenerates byte for byte (fixed timestamps for the
  embedded figures), drops an unused template hyperlink, and names the documents
  that cover interactive allocations; `NOTICE` credits the card's template.
- Document deployment trust assumptions in `SECURITY.md` and the request fields
  that reach vLLM in the API reference.
- Remove the built-in PBS account and project root: `EXASERVE_PROJECT_ACCOUNT`
  (or `--project-account`, `scheduler.project`, `--account`) and
  `EXASERVE_PROJECT_ROOT` must now be set, and commands that need them fail with
  an error that names them. Allocation campaigns record the account they were
  created with.
- Replace PBS job identifiers in published records with labels. The legacy
  paper-evidence ledger moves to schema 3 without job identifiers; its loader
  reads them from the pinned PBS stdout file name.
- Remove maintainer home-directory defaults. The serving launcher sources the
  script that `EXASERVE_ENV_SCRIPT_AURORA` names (otherwise it loads the
  frameworks module); allocation campaigns record the site environment script
  and PBS output directory in a schema-2 campaign identity; eval run snapshots and
  benchmark results default to the configured data root; the LiteLLM interpreter
  and environment scripts have no default location.
- Publish `main` only (the path migration guide says so) and keep the issues
  that recurred on the retired branches in `docs/KNOWN_ISSUES.md`.
- Gather every plotting script in `eval/plot/` under a descriptive name (the
  root `plot/` script, three from `eval/scripts/` and one from `benchmarks/`)
  and rename the base matplotlib style; remove the empty `.codex` file, which
  is now ignored; cite the paper on arXiv instead of naming a development
  branch.
- Remove run logs, audits, campaign records and research notes from the current
  tree and collect their lessons in `docs/operations_handbook.md`: deployment
  prerequisites, measured limits, failures seen and their fixes, settings that
  worked, and measurement and qualification practice. The hardening status and
  open-work pages now describe the current state only; the removed records
  remain in the repository history. Remove an unused copy of an old broadcast
  helper from `tools/`.
- Reject request-supplied chat templates and reserved `chat_template_kwargs`
  keys with HTTP 400, require a model configuration's `model_type` to match its
  reviewed architecture before broadcast, and load evaluation tokenizers
  without remote code.

### Documentation paths

- Consolidate architecture, hardening records and research findings under
  `docs/`.
- Update documentation, analysis and reference-card paths; check local links in
  CI against tracked files. The later retirement of run records updates ledger
  references while preserving recorded finding dispositions, artifact hashes
  and qualification/profile identities.

### Portable CI

- Give GitHub-hosted staging tests a separate `/tmp` tmpfs so real shared/local
  filesystem guards can run without assuming Aurora's mount layout.
- Declare Ray/FastAPI requirements for optional Serve graph tests and keep
  source-order and deployment-plan checks independent of those dependencies.
- Hash the arrival CSV only for Azure replay. Synthetic and dataset-replay
  trace identities no longer require an unused site-default Azure dataset.

### Serve application layout

- Deploy a dense real-engine model (one HAProxy model, TP=1, PP=1, every GPU of
  every node) as one Serve application with one multi-replica deployment
  instead of one application per replica. Each replica still resolves and
  attests its exact rank/device slot; HAProxy no longer selects a replica
  route for this layout, Serve's router does. Sparse, multi-device,
  pipeline-parallel and multi-model topologies keep one application per
  replica, and dense null-compute keeps its node-grouped applications.
  Covered by hermetic tests only; no hardware qualification is implied.

### Repository preparation for AI-ModCon

- Adopt Apache-2.0 licensing and explicit maintainer/contact metadata.
- Add contribution and conduct policies, private security reporting, and issue
  and pull-request templates with human-review and AI-assistance disclosure.
- Add a `docs/` navigation and onboarding layer while retaining the existing
  `doc/` architecture contracts, design notes, and immutable evidence references.
- Add locked portable development tooling, coverage configuration, build
  automation, and a transfer/branch-protection checklist.
- Preserve the existing hermetic, randomized, installed-wheel, static, and Go
  CI gates; do not imply new hardware validation from repository housekeeping.

### Existing scaling and hardening baseline

`main` incorporates the scaling and hardening history through `044d3ef`:
head-owned source/model distribution, typed MPI
replay aggregation, bounded lifecycle ownership, exact readiness evidence,
node-local compatibility state, and qualified finite allocation-subset tooling.

The 405B sequential campaign's model-staging storage failure and missing
64-/128-node measurements remain unresolved. Paper results and earlier package
gates do not establish a complete production release or Frontier support.

## Historical 0.4.0 candidate

The package version remains `0.4.0`; this entry does not create a release or tag.
The `release-v0.4.0-rc2` package and earlier evidence are summarized in
[`docs/hardening/STATUS.md`](docs/hardening/STATUS.md), which explains why
they do not qualify the current tree.
