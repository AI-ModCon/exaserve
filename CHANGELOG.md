# Changelog

This records project changes, not an assertion that a deployment or release has
passed hardware qualification. Exact artifacts and scope are recorded in
[`docs/hardening/STATUS.md`](docs/hardening/STATUS.md) and the linked evidence.

## Unreleased

### Publication readiness

- Name `AI-ModCon/exaserve` in package metadata, documentation and contribution
  links, and record the transfer in the AI-ModCon checklist.
- Redact maintainer account paths, compute-node names, allocation-internal
  addresses and a reservation identifier from documentation, example and
  hardening configurations, frozen evaluation specs and test fixtures; remove
  the personal development scratchpad; regenerate the reference card.
- Refresh the portable development lock with uv 0.13.4 and fixed releases of
  Pillow, pytest, Pygments, fontTools, certifi, aiohttp and virtualenv. The lock
  now resolves Python 3.11–3.13. Server extras and site runtime pins are
  unchanged; remaining dependency advisories are dispositioned in the
  AI-ModCon checklist.
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
- Label compute nodes in published records as `node-<rack>-<chassis>-<slot>`,
  list the branches retired before publication in the path migration guide, and
  keep the issues that recurred on them in `docs/KNOWN_ISSUES.md`.
- Reject request-supplied chat templates and reserved `chat_template_kwargs`
  keys with HTTP 400, require a model configuration's `model_type` to match its
  reviewed architecture before broadcast, and load evaluation tokenizers
  without remote code.

### Documentation paths

- Consolidate architecture, hardening records and research findings under
  `docs/`.
- Update documentation, analysis and reference-card paths; check local links in
  CI against tracked files. Historical ledger bytes and qualification/profile
  identities are preserved through documented legacy-reference resolution.

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

`main` incorporates the history through `044d3ef` from
`paper/missing-scale-v0.4.0`: head-owned source/model distribution, typed MPI
replay aggregation, bounded lifecycle ownership, exact readiness evidence,
node-local compatibility state, and qualified finite allocation-subset tooling.

The 405B sequential campaign's model-staging storage failure and missing
64-/128-node measurements remain unresolved. Paper results and earlier package
gates do not establish a complete production release or Frontier support.

## Historical 0.4.0 candidate

The package version remains `0.4.0`; this entry does not create a release or tag.
The `release-v0.4.0` baseline and `v0.4.0-rc2` evidence are preserved in
[`doc/hardening/STATUS.md`](docs/hardening/STATUS.md). Its supersession notice
explains why earlier artifacts do not automatically qualify the current tree.
