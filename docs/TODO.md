# ExaServe open work

**Role:** non-normative backlog. The
[execution plan](PRODUCTION_HARDENING_EXECUTION_PLAN.md) defines architecture
and the [findings ledger](hardening/FINDINGS.yaml) defines disposition; this
file cannot waive a gate. The current qualification state is in the
[hardening status](hardening/STATUS.md); behaviour seen in measurements and the
questions it left open are in the
[operations handbook](operations_handbook.md#10-open-problems).

## Release-gating actions

1. Product owner: approve the proposed 64-node first-release ceiling or select
   a lower ceiling.
2. After that decision, predeclare and run only the matching ladder from one
   immutable candidate. A 64-node choice requires 4, 16 and 64 nodes with the
   same wheel.
3. Update ADR-000, the compatibility matrix, the ledger and the release verdict
   from those exact receipts. Do not substitute runs from other code or earlier
   candidates.

## Open ledger records

These are the eight `IN_PROGRESS` ledger records; all depend on scale or scope
evidence rather than an unresolved two-node code defect:

| ID | Required next proof |
|---|---|
| `PR-033` | Owner-approved envelope and exact-candidate qualification at its boundary. |
| `KI-A1` | Only if Envoy, streaming or 256 nodes enters scope: reproduce with owned failure evidence. |
| `KI-A3` | Measure Ray GCS and controller behaviour of the current candidate at the approved boundary. |
| `KI-A7` | Measure residual shared-environment imports at the approved scale. |
| `KI-B2` | Only if streaming enters scope: capture the rare HAProxy death's real cause. |
| `KI-D2` | Prove native distribution and every activation receipt at the approved boundary. |
| `TD-COPPER` | Quantify residual shared-filesystem import traffic at that boundary. |
| `IMP-B16` | Freeze the already-implemented plan family against the approved and measured envelope. |

## Known defects to fix

- Add the layer-fallback warnings to the engine receipt
  ([D5](KNOWN_ISSUES.md#d5-pipeline-parallel-patches-fall-back-to-a-representative-layer--fails-closed-in-production)).
  The real PP=2 two-node canary was rerun on 2026-10-22 under the new
  layer-fallback policy in validation mode and showed no fallback warning.

## External platform qualification

`TD-SLURM-AMD` is `EXTERNAL_BLOCKER`. The scheduler and vendor abstractions and
failure contracts are unit-tested, but production support requires a native
Slurm allocation with a pinned CUDA or ROCm stack. When such a system is
available, qualify device isolation, dependency profile, HAProxy availability,
multi-node launch, PP placement, process failure, readiness and cleanup. Until
then the selected SiteProfile rejects the combination.

SGLang is explicitly gated out of the selected Aurora profile (`TD-SGLANG`).
Adding it is a new compatibility and site profile with its own clean package,
real-engine, failure and scale evidence; the existence of `SGLangEngine` is not
a support claim.

## Optional work outside the current production release

- `TD-CACHE`: proxy-layer request caching and deduplication.
- `TD-STAGE-PAR`: concurrent multi-model download. Transactional serial staging
  remains correct; revisit only if start-up targets make parallelism necessary.
- `TD-CPP-CLIENT`: a C++ client experiment for research only. The Go replay
  client is the benchmark client.

## Research and measurement ideas

- Strong scaling (fixed workload, more nodes) and tail latency (p99 and p999
  from the Go client histograms).
- 405B non-streaming at 64 and 128 nodes (`pp405b_pp2_haproxy_nostream_v040`):
  the sequential allocation-campaign attempt failed during model staging
  (storage), and those points are missing; the retained records do not
  diagnose the failure.
- Measure latency through a LiteLLM hop, clearly labelled as validation-only
  and not real streaming.
- Isolate proxy overhead with matched request and client topology.
- Compare error rates with and without explicit retry policies.
- Explore distributed or sharded ingress if an approved envelope exceeds the
  measured single-head HAProxy boundary.
- Evaluate a sharded control plane only if measurements at the approved scale
  show that Ray's controller is the limiting factor.

## Closed backlog items

These former backlog items are closed in the ledger, which records their
evidence:

- `TD-TESTS`: hermetic and packaged CI, typing, linting, security and
  failure-path tests;
- `TD-NULLTOK`: exact null-compute and tokenizer identity, and capability
  labelling;
- `TD-PORTS`: OS-owned, leased ports and deliberate collision failure;
- `TD-CHATTPL`: loud, capability-gated chat-template fallback;
- `TD-REQID` and `TD-METRICS`: request-ID correlation and a bounded `/metrics`;
- `TD-CONSTS`: site constants centralized in the SiteProfile;
- `TD-SITECUST`: exact-hash generated compatibility delivery with no edits to
  installed files;
- `TD-PP-MULTI`: explicit PP topology and capability gating, and a real
  two-host PP=2 proof;
- `TD-PROXYPROF`: the legacy proxy-profiling owner retired;
- `TD-PSIJ`: one scheduler abstraction, with PSI/J a dependency only when
  selected;
- `TD-DOCS-REGEN`: documented, path-independent, atomic reference-card
  regeneration (the ignored template and two figure prerequisites are listed in
  [docs/exaserve.md](exaserve.md)).
