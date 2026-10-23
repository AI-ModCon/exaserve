# AI-ModCon repository preparation checklist

This checklist applies the **Required Elements for ModCon Base Public
Repositories** in [AI-ModCon/BaseTemplate](https://github.com/AI-ModCon/BaseTemplate/blob/fcfc042ffe287af9526520dd3e10b88dcd127d3b/README.md),
reviewed at commit `fcfc042ffe287af9526520dd3e10b88dcd127d3b` on 2026-09-23
and checked against the same current template revision on 2026-10-20.
The public-readiness review of 2026-10-21 is recorded
[below](#public-readiness-review-2026-10-21). This checklist records repository
preparation, not approval of a production release or of public visibility, and
not new hardware qualification.

## Repository location

The repository was transferred from `globus-labs/exaserve` to
**`AI-ModCon/exaserve`** with its history, issues, pull requests, branches and
tags. On 2026-10-21 it was private in the AI-ModCon organization. Package
metadata, documentation and contribution links name `AI-ModCon/exaserve`.

The current integration adds the plan-derived dense real-engine
single-application layout from `afb0349` and repairs portable CI's site
assumptions. `/tmp` is provisioned as a separate tmpfs on disposable hosted
runners, optional Serve API tests declare their Ray/FastAPI requirements, and
non-Azure traces no longer hash an unused site-default arrival CSV. These
changes do not create new hardware or scale qualification.

### Validation evidence (2026-10-20)

The runtime/CI repair candidate is `67253ade6c3b9689f335bf51bf1473696467a9a8`.
Its own GitHub CI run was cancelled, so it is not the record; CI passed on
`main` with this candidate in
[run 39470617396](https://github.com/AI-ModCon/exaserve/actions/runs/39470617396)
(`d12f972`) and
[run 39637778628](https://github.com/AI-ModCon/exaserve/actions/runs/39637778628)
(`3487041`). The results recorded for the candidate were:

- Python 3.12 fixed-order coverage suite: **1,720 passed, 42 skipped**;
  portable branch/statement coverage is 60%, with an uploaded XML report.
- Python 3.12 randomized-order suite: **1,720 passed, 42 skipped**.
- Clean installed-wheel suite: **1,720 passed, 42 skipped**; the audited sdist
  and wheel build and packaged-resource checks passed.
- Portable lock checks for Python 3.10/3.12, Go tests, findings validation,
  formatting, lint, typed-core and security checks passed.

The optional Serve tests were also exercised with their real import-time
dependencies in one allocated Aurora node:
**152 focused unit tests passed**. The command was:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  python3 -m pytest -q -p no:randomly \
  tests/test_single_application_layout.py tests/test_null_application_grouping.py \
  tests/test_server_failure_diagnostics.py tests/test_engine_attestation.py \
  tests/test_source_staging.py eval/tests/test_trace_identity.py
```

This used the current site framework (Python 3.12.12, Ray 2.56.1,
pytest 9.0.3), with no live model, GPU, MPI or serving-cluster launch. These
are unit-test results, not qualification of either serving stack.

At the owner's request, current CI targets Python 3.12, matching Aurora's
current Python 3.12.12. The earlier Python 3.10 job is superseded and is not a
release gate. Later commits change runtime code, so the CI run on the final
pull request, not this record, covers the published tree.
Check the final `main` CI run and live GitHub protection after integration;
neither this record nor a checked-in JSON file substitutes for those checks.

## Requirement mapping

| BaseTemplate requirement | ExaServe implementation | Remaining gate |
|---|---|---|
| Open-source license and package declaration | [LICENSE](../LICENSE), [NOTICE](../NOTICE), Apache-2.0 metadata in [pyproject.toml](../pyproject.toml) | Maintainers retain responsibility for contribution and third-party rights |
| `docs/`, README, onboarding and examples | [Documentation index](index.md), [getting started](getting_started.md), [usage](usage.md), [API](api.md), [FAQ](faq.md), [README](../README.md) | Maintain links and examples as the project evolves |
| pytest suite and coverage | Existing three test trees; explicit coverage configuration and CI reports | Run and review the updated CI; coverage is not hardware evidence |
| CI/CD test integration | Existing hermetic, randomized-order, installed-wheel, Go, ledger and static jobs retained; portable lock lane added | Require these checks with branch protection (step 3 below) |
| Contribution and AI-assistance policy | [CONTRIBUTING](../CONTRIBUTING.md), [PR template](../.github/pull_request_template.md) | A human must review and approve changes |
| Conduct policy and issue procedures | [CODE_OF_CONDUCT](../CODE_OF_CONDUCT.md), [issue templates](../.github/ISSUE_TEMPLATE), [SECURITY](../SECURITY.md) | Maintain the private contact and triage reports |
| Main-branch protection | Administrator instructions below | **Requires GitHub settings; not applied on `AI-ModCon/exaserve` as of 2026-10-21** |
| Project, author/contact, dependency and Python metadata | [pyproject.toml](../pyproject.toml); Wenyi Wang, `wenyiw@uchicago.edu` | Update contacts whenever ownership changes |
| Development automation and lock | [Makefile](../Makefile), [uv.lock](../uv.lock), [dependency profiles](../requirements/README.md) | Run the locked portable CI on the current Aurora Python minor version (3.12) |
| Genesis Mission acknowledgment | [README acknowledgment](../README.md#acknowledgments) credits support for the ModCon Base collaboration | Confirm project-specific wording if an institution requires it |

The additional changelog and private security policy follow the template's
repository conventions. No automatic PyPI publication, external coverage
service, new access token, or unreviewed deployment workflow is enabled.

## Public-readiness review (2026-10-21)

Issue [#2](https://github.com/AI-ModCon/exaserve/issues/2) reviewed `main` at
`34870417` against BaseTemplate. It listed three blockers for public
visibility, operational details, dependency alerts and unenforced review and
CI policy, plus outdated repository links and disabled security features.

| Review item | Repository change | Still required |
|---|---|---|
| Operational details | Current-tree account paths, compute-node names, allocation-internal addresses, a reservation identifier and PBS job identifiers redacted ([publication redaction](path_migrations.md#publication-redaction)); the allocation name removed from the current tree, with no default PBS account or project root left in code; personal development scratchpad removed; reference card regenerated | Remove the three pre-publication tags and every non-main branch before the visibility change ([decision](#operational-details-kept-for-the-disclosure-decision)) |
| Dependency alerts | Development lock refreshed; upgrades are expected to close 75 of the 126 alerts open on 2026-10-23 once integrated; request chat templates rejected and model types pinned | Verify the upgrade results and review and record the remaining 51 proposed dispositions below |
| Review and CI enforcement | The [protection payload](../.github/main-branch-protection.json) already names the seven current CI checks and the required review settings | Apply it (step 3 below) and read it back |
| Repository links | Package metadata, README, documentation and this checklist name `AI-ModCon/exaserve` | — |
| Security features | Trust assumptions documented in [SECURITY.md](../SECURITY.md#deployment-trust-assumptions) | Enable them (step 5 below) |
| Release description | README describes the repository as development and research source, not a production-qualified release | Describe the visibility change the same way |

### Operational details kept for the disclosure decision

On 2026-10-22 the project decided that Git history is not rewritten, that
the current tree must carry neither the identifiers listed under
[publication redaction](path_migrations.md#publication-redaction) nor run
history, and that the
tags `v0.1.0`, `v0.2.0` and `v0.4.0-rc2` and the 15 non-main branches are
removed before the visibility change. The current tree retains:

- Aurora site names that ALCF's public user guides
  ([argonne-lcf/user-guides](https://github.com/argonne-lcf/user-guides))
  also print: the `/home` and `/lus/flare` shared-filesystem roots, the
  `.hsn.cm.aurora.alcf.anl.gov` high-speed-network domain, the
  `aurora-pbs-0001.hostmgmt.cm.aurora.alcf.anl.gov` PBS server name, the
  `aurora-uan-*` login-node pattern and the shared model-weights directory
  `/lus/flare/projects/datasets/model-weights` (ALCF's guides print it as
  `/flare/datasets/model-weights`, the same directory).
- Aurora's platform name, platform-specific tuning, and standard queue names
  remain part of the reference deployment. The queue names are documented in
  [ALCF's public running-jobs guide](https://docs.alcf.anl.gov/aurora/running-jobs-aurora/).
- The maintainer contact `wenyiw@uchicago.edu` in package metadata,
  SECURITY.md and the Code of Conduct.
- Run logs, audits, campaign records and research notes were removed from the
  current tree. Their lessons are in the
  [operations handbook](operations_handbook.md), which keeps measurements and
  failure analyses without job, host or run identifiers.

Earlier commits keep their original content; removing the branches and tags does
not change what `main`'s history holds.

Hardening found while triaging the alerts, also part of this change: a request
can no longer supply its own Jinja chat template (the resource-exhaustion
pattern of CVE-2025-61620, which vLLM's own server refuses by default); staging
rejects a model configuration whose `model_type` is not the reviewed type for
its architecture; and the evaluation tools load tokenizers without remote code.

### Dependency alerts

On 2026-10-23 GitHub listed 126 open alerts on `main`, all from `uv.lock`: the
92 recorded in the 2026-10-21 review and 34 filed since. The development lock
is now generated with uv 0.13.4 and resolves Python 3.11–3.13. The test group
pins Pillow 13.0.0, pytest 9.0.3, Pygments 2.20.0 and fontTools 4.60.2, also in
`requirements/ci.lock`, and the transitive certifi (2026.10.19), aiohttp
(3.14.5), virtualenv (21.14.5) and OpenTelemetry (1.45.1) resolutions were
refreshed. These upgrades are expected to close 75 of the open alerts; verify
the result after integration. The refresh does not change the ALCF-supplied
frameworks module, which keeps certifi 2026.1.4, aiohttp 3.13.3 (3.13.2 vendored
in Ray's runtime-environment agent), Pillow 12.1.0 and virtualenv 20.36.1; their
exposure falls under SECURITY.md's trusted-network assumption, with text-only
requests and no virtualenv creation.

The other 51 cannot be closed by upgrading without changing the qualified
serving stack, the audited build tools, or the pins and extras named below. Each was checked against the code
paths that ExaServe uses and against the request surface in the
[API reference](api.md#inference-http-surface):

| Package | Alerts | Locked | Why it stays | Disposition |
|---|---:|---|---|---|
| vllm | 31, one critical | 0.15.0 | Exact pin of the qualified `frameworks/2025.3.1` stack | 30 unreachable: ExaServe does not run vLLM's OpenAI server, passes only a text prompt and six validated sampling fields, and serves text-only Llama and GPT-OSS checkpoints; five of the 30 concern code that vLLM 0.15.0 does not contain. 1 accepted: a low-severity KV-block reuse defect |
| transformers | 5 | 4.57.6 | Exact pin of the qualified stack and the `paper` extra | Unreachable: no Trainer, `save_pretrained`, custom generation or Hub kernels, and staging rejects a configuration whose `model_type` would select another model class |
| ray | 3 | 2.53.0 | Exact pin of the qualified stack | Unreachable: no Ray Data, no Ray Jobs, dashboard disabled |
| torch | 2 | 2.9.1 | Pinned by vLLM 0.15.0 | Unreachable: neither affected API is called |
| xgrammar | 1 | 0.1.29 | Pinned by vLLM 0.15.0 | Unreachable: no structured-output request reaches vLLM |
| diskcache | 1 | 5.6.3 | Pinned by vLLM 0.15.0; no fixed release | Unreachable: vLLM's outlines cache is never used |
| datasets | 1 | 4.8.5 | The `paper` extra requires `<5` | Unreachable: no folder-based builder is used |
| fsspec | 1 | 2026.2.0 | Capped by datasets 4.x | Unreachable: no reference filesystem is opened |
| virtualenv | 5 | 21.14.5 | 21.14.7 and later need packaging 26.3; the test group and `requirements/ci.lock` pin packaging 25.0, and psij-python 0.9.4 and later (the `scheduler` extra; 0.9.11 is locked) cap it at 25.0 or lower, so lifting the pin would pull psij-python back to 0.9.3 | Unreachable: no virtualenv is created or activated |
| setuptools | 1 | 78.1.1 | Audited build backend; vLLM 0.15.0 requires `<81` | Accepted: needs non-ASCII exclusions built on macOS APFS/HFS+; releases are built on Linux by the audited builder, which rejects unexpected sdist members |

Have the responsible maintainer review each of the 51 proposed dispositions.
Record the resolution or justified dismissal with its reason and a comment
citing the supporting code or document. Every critical and serving-stack
finding needs an explicit disposition; an empty alert list alone does not
establish that triage is complete. Review the list again whenever the lock or
the site stack changes, and triage new advisories against the pinned stack the
same way as they arrive. Requalifying on a newer site stack would close most of
the vLLM alerts by upgrade.

## Adaptations that preserve ExaServe's contracts

- Keep `src/exaserve`, rather than moving the package to match the example
  layout. Keep `docs/PRODUCTION_HARDENING_EXECUTION_PLAN.md` authoritative and
  retain historical artifact identities. Guides, design, hardening records and
  research findings are consolidated in `docs/`; the
  [path migration guide](path_migrations.md) explains historical aliases.
- Preserve Python `>=3.10` package metadata while targeting Python 3.12 in CI,
  as requested by the owner. The uv resolution envelope is Linux and Python 3.11–3.13 because
  the existing optional vLLM extra excludes Python 3.14 and Pillow 13.0.0, the
  first release without its known advisories, requires Python 3.11. This does not qualify
  another interpreter, operating system, engine or accelerator.
- Preserve existing server extras and site runtime pins. The default uv groups
  install portable development/test tools, not Ray, vLLM or PyTorch. The lock
  contains optional dependency resolutions too; their presence does not mean
  they are installed by default or qualify an HPC stack.
- Keep the standalone `requirements/ci.lock` installation for the independent
  installed-wheel gate. The portable uv lane checks installed versions against
  that profile and rejects accidental installation of the GPU stack.
- Keep exact source-distribution/package-member checks. Release input staging
  explicitly includes the license, notices and lock; wheel auditing verifies
  SPDX metadata and the exact packaged license/notice bytes.
- Do not copy BaseTemplate's broad recursive cleanup commands, placeholder
  security email, unsupported version table, funding identifiers, Python 3.14
  support claim, or automatic publishing setup.
- The initial repository-conventions pass added no Frontier profile and changed
  no serving/compatibility behavior. The later dense-application integration is
  separately scoped. Hardware evidence remains tied to its original commit,
  profile, dependencies and configuration.

## GitHub administrator steps

These steps are **not completed by adding files** and must be reviewed by the
repository owners. Do not mark this checklist complete until the actual settings
and successful CI runs have been checked.

**Owner instruction, 2026-10-20:** merge the deployment change into `main` and
finish BaseTemplate preparation. This supersedes the 2026-09-23 deferral of
branch protection. Integrate and validate the changes, then apply the required
review/check protection; do not claim a human review that has not occurred.

The reusable [branch-protection payload](../.github/main-branch-protection.json)
requires one approving review, an approval of the latest push by someone other
than its pusher, dismissal of stale reviews, resolved conversations, and all
seven CI checks from GitHub Actions. It also applies to administrators and
disables review bypasses, force pushes and branch deletion. GitHub cannot
determine whether every approving account is a human, so maintainers must
continue to enforce the human-review policy in CONTRIBUTING.md.

After checking successful CI and the authenticated administrator's authority,
apply it with GitHub CLI (or the equivalent authenticated REST request):

```bash
gh api --method PUT repos/AI-ModCon/exaserve/branches/main/protection \
  --input .github/main-branch-protection.json
gh api repos/AI-ModCon/exaserve/branches/main/protection
```

The JSON file is a configuration input, not proof that protection is active.
On 2026-10-21 `AI-ModCon/exaserve` had no branch protection and no rulesets,
so the payload still has to be applied there.

1. Done: the repository was transferred with its commit history, branches,
   tags, issues and evidence links. Do not create a replacement history by
   copying files into an empty template repository.
2. Done (read on 2026-10-23): the repository's Actions policy permits the pinned
   actions in [CI](../.github/workflows/ci.yml), the workflow token is
   read-only and Actions cannot approve pull requests. Keep it that way, and do
   not expose privileged credentials to untrusted PR code.
3. Protect `main` with a ruleset/branch protection requiring pull requests,
   at least one approval from a human reviewer other than the author, dismissal
   of stale approvals, resolved review conversations, and required CI checks.
   Restrict bypass permissions; disable force pushes and branch deletion.
   Configure actual human/team ownership after the team names and access are
   confirmed; do not use a guessed CODEOWNERS entry.
4. Require the exact checks that CI emits:
   `portable uv lock (py3.12)`, `Go replay client tests`,
   `hermetic tests (py3.12, fixed)`, `hermetic tests (py3.12, random)`,
   `packaged wheel test (not an editable checkout)`,
   `findings ledger validator`, and `format + lint + type + security`.
   Reconcile these names with the actual runs before enforcing the rule.
5. Enable Dependabot security updates, secret scanning with push protection
   and non-provider patterns, code security with CodeQL default setup, and
   private vulnerability reporting. On 2026-10-21 all of these were disabled.
   Dependabot security updates work on a private repository. Secret scanning
   and CodeQL/code scanning on private repositories depend on the organization's
   applicable licenses. Private vulnerability reporting is a
   [public-repository feature](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository);
   enable it as part of the visibility change. Arrange platform secret scanning
   of the full history before or as part of that change and resolve its alerts.
   The published email route in
   [SECURITY.md](../SECURITY.md) works independently of private reporting;
   confirm a responsible maintainer monitors it. Do not publish reports as issues.
6. Done: package metadata, README, documentation and community guidance name
   `AI-ModCon/exaserve`. Update maintainer contact details whenever ownership
   changes.
7. Review any future package publishing separately: registry ownership, release
   evidence, protected environments and trusted publishing are distinct actions.
   Do not introduce a publish token or deploy-on-push workflow.
8. Before changing visibility, remove the tags `v0.1.0`, `v0.2.0` and
   `v0.4.0-rc2` and every non-main branch: the 15 audited ones, #3's branch and,
   once it is merged, the cleanup pull request's branch. The
   [audited branches](path_migrations.md#retired-branches) and their recurring
   lessons ([known issues](KNOWN_ISSUES.md#lessons-kept-from-retired-branches))
   are recorded.
