# ExaServe production-hardening status

> **Current verdict: no production-qualified artifact.** This tree is
> development and research source. Production submission fails closed with
> `production execution is not qualified`. Hardware work needs authorized,
> predeclared `validation_mode: true`, which records `production_qualified=false`
> and cannot establish support.

## What the current tree is and is not qualified for

- **Production serving:** not qualified at any node count. The Aurora
  `SiteProfile` has no measured control and readiness limits, and its proposed
  64-node envelope has no product-owner approval.
- **Compiled ceiling:** plans compile to at most two nodes
  (`supported_max_nodes=2`), the last measured boundary. This is a limit carried
  in code, not evidence for this tree.
- **Portable tests:** they show code behaviour; they are not hardware
  qualification.
- **Target dimensions once qualified:** Aurora PBS; Intel PVC/XPU, 12 tiles per
  node; vLLM under the pinned frameworks profile; HAProxy on the allocation head;
  non-streaming completions; trusted allocation-internal network. Slurm,
  CUDA/ROCm, SGLang, streaming, public or direct exposure and other gateways are
  unsupported or validation-only.

## What a new qualification requires

1. One clean candidate: sdist and wheel built in an isolated environment; the
   exact wheel installed into a clean environment; the full suite, resource
   checks, typed-core mypy, Ruff, compileall, Go checks and findings validator
   run outside the source tree on a compute node.
2. The non-head shared-filesystem gates in section 3.2.1 of the
   [execution plan](../PRODUCTION_HARDENING_EXECUTION_PLAN.md), including a
   two-node syscall trace from managed-process creation that shows zero
   non-head opens under declared shared roots, and per-rank shared-open
   telemetry at every claimed scale.
3. One- and two-node hardware cells from that wheel: null and real-engine
   lifecycles, PP=2 across two hosts, drain, gateway death, worker loss,
   duplicate port, partial readiness, Ray-head and supervisor faults, and
   cleanup with zero exact-generation survivors.
4. Measured `SiteProfile` control and readiness limits.
5. A recorded product-owner decision on the release ceiling
   ([ADR-000](decisions/ADR-000-production-envelope.md) proposes 64 nodes), the
   predeclared ladder for it (4, 16 and 64 nodes for 64) through
   `scripts/hardening/run_scale_qualification.py`, and a new candidate review
   binding every receipt.
6. For logical subsets inside a larger allocation: a new four-physical,
   two-logical-node proof of the current allocation controller.

## Historical evidence and why it does not carry over

| Evidence | What it covered | Why it does not qualify this tree |
|---|---|---|
| `final43` package | one and two Aurora nodes, validation mode | built before the non-head shared-filesystem cutover changed runtime, harness, model-manifest and result identities |
| `release-v0.4.0-rc2` package | clean package gate only | same cutover; no hardware ladder ran |
| Later campaign runs | null-compute start-up at 32 and 64 nodes, 405B PP at 4, 8 and 256 nodes, the allocation-subset proof | an earlier snapshot in validation mode; the runtime and allocation controller changed afterwards |
| Earlier previews and research runs | 4-, 16- and 64-node previews and larger research runs | other code; regression context only |

Do not update old artifact hashes to match new code, relabel old receipts, or
join runs from different snapshots into one scaling curve. Earlier revisions of
this page and the retired run records remain in the repository history. Wheel
SHA-256: `final43` `1041be53eb5b5875d198d5ee6c6664718b4085775dcba99107873dd3d1fcdff2`;
`release-v0.4.0-rc2` `75bab1c97948d29237000d5fa087f3ed1f1d18e5ef3233fe2c759b4faf0e32f8`.

## Ledger

The [findings ledger](FINDINGS.yaml) validates against its exact schema. Its
open records (eight `IN_PROGRESS`, one `EXTERNAL_BLOCKER`) and the work that
would close them are listed in [open work](../TODO.md).

See also the [compatibility matrix](COMPATIBILITY_MATRIX.md),
[known issues](../KNOWN_ISSUES.md) and the
[operations handbook](../operations_handbook.md), which records measured
behaviour, limits and lessons from earlier campaigns.
