# ExaServe runtime and demonstrated scale matrix

**Demonstrated research scale: 1–256 Aurora nodes**, measured on earlier
snapshots of this code; the current tree has not been re-measured at that
scale. The [paper](https://arxiv.org/abs/2609.10812) evaluates the serving
system through 256 nodes; the [operations handbook](../operations_handbook.md)
records measured throughput and configuration-specific limits, including
pipeline-parallel 405B serving at that scale.

This matrix distinguishes measured system capability, selected runtime
identities and packaged-release admission. Coverage of later fixes and earlier
package gates is recorded in the
[changelog](../../CHANGELOG.md#validation-coverage). No artifact is
production-qualified ([release status](STATUS.md)).

## Exact software profile

| Component | Selected identity | Qualification note |
|---|---|---|
| ExaServe, recorded `final43` package (not the current tree) | 0.4.0 wheel SHA `1041be53eb5b5875d198d5ee6c6664718b4085775dcba99107873dd3d1fcdff2` | verification scope in the changelog |
| ExaServe, recorded `release-v0.4.0-rc2` package (not the current tree) | 0.4.0 wheel SHA `75bab1c97948d29237000d5fa087f3ed1f1d18e5ef3233fe2c759b4faf0e32f8` | clean package gate passed; production scale unqualified |
| Aurora frameworks | 2025.3.1 | recorded reference environment |
| Python | 3.12.12 | packaged and hardware gates |
| Ray | 2.53.0, commit `0de2118` | exact base hashes; generated overlay; installed files untouched |
| vLLM | 0.15.0+xpu | reference engine for the Aurora evaluations |
| transformers | 4.57.6 | selected environment |
| torch | 2.10.0a0 XPU | selected environment |
| HAProxy | executable identity recorded per run | owned and native-config validated |

Candidate-bound hashes:

- site profile: `4814429547fd4397014819a0f8b5c6ec8f7d77c889eaf844d27935b39a0a6e26`;
- compatibility profile: `c17e684fe485261a9cfa82248bd24a9209b66a7c66bae8b889b24ca878d335d3`;
- compatibility manifest: `cd85123822f4b936216282ed43346223a4b68f1a7cb152a85715a36fdab24259`.

These candidate-bound identities are preserved as recorded. A dependency or
identity change requires its affected release-validation cells to be checked.

## Dimension matrix

| Dimension | Reference profile / demonstrated use | Additional validation / release gates | Rejected by the default profile |
|---|---|---|---|
| Site/scheduler | ALCF Aurora with native PBS | PSI/J rendering/interface tests | Native Slurm production use |
| Accelerator | Intel PVC XPU, 12 tiles/node | — | CUDA and ROCm until offsite qualification |
| Engine | vLLM | null engine for lifecycle faults | SGLang in the selected profile |
| Gateway | HAProxy | LiteLLM, Envoy, NGINX, Pingora adapters | Unowned/unprofiled gateways |
| Exposure | `PROXIED_INTERNAL` on trusted allocation network | `DIRECT_VALIDATION` | public Internet/direct Serve production exposure |
| API/mode | OpenAI-compatible non-streaming completion | streaming/chat/mixed experiments; LiteLLM buffered throughput/error evidence | buffered, coarse, or unclassified timing represented as incremental TTFT/TBT |
| Model topology | TP=1/PP=1 serving and multi-node TP/PP inference, including TP=8/PP=2 for 405B | explicitly gated runtime combinations | topology outside the canonical capability set |
| Scale | Aurora serving evaluations through 256 physical nodes, on earlier snapshots | validation-mode plans: up to 64 nodes in the reference envelope, up to the 256-node site maximum in other gateway, exposure, request or streaming dimensions; the proposed packaged release has a separate exact-candidate ladder | non-validation plans above two nodes; reference-envelope plans above 64 nodes; any plan above the site maximum |

The selected release-admission envelope is
`aurora-xpu-vllm-haproxy-completion-non_streaming-candidate64`. It records
`supported_max_nodes=2`, `qualification_target_nodes=64`,
`qualification_target_approved=false` and `validation_mode=false`, and the
compiler enforces it: a non-validation plan of 3–64 nodes fails with
`exceeds evidence-backed supported maximum 2` and a larger one with `exceeds
candidate qualification target 64`, and a production submission that compiles
fails closed with `production execution is not qualified`. Validation-mode
plans in this envelope compile up to its 64-node qualification target
(`EXASERVE_QUALIFICATION_TARGET_NODES`); plans that differ in gateway, exposure,
request or streaming mode compile, in validation mode only, into the generic
envelope up to the site maximum (`EXASERVE_SITE_MAX_NODES`, 256 by default);
other schedulers, vendors and engines are rejected. These admission limits are
separate from the 256-node measurements.

## Scale tiers

| Physical nodes | Recorded system evaluation (earlier snapshots) | Notes |
|---:|---|---|
| 1–256 | Llama-3-8B serving, gateway comparison, streaming and non-streaming measurements | workload and gateway limits are recorded in the paper and handbook |
| 4–256 | Llama-3.1-405B pipeline-parallel inference, up to 128 replicas | measurements bind their source, model and runtime configurations |
| 32, 64, 256 | null-compute start-up and control-plane measurements | complements inference measurements with control-plane behaviour |

These measurements establish the demonstrated scale of ExaServe; they do not
qualify the current tree. A focused regression check at a smaller allocation
verifies its named change; it is not a new system-wide scale ceiling.

## Qualification semantics

Packaged-release validation must bind:

- exact scheduler membership and authenticated per-rank sessions;
- exact source-staging and compatibility receipt sets;
- planned Ray resources, Serve applications/replicas, and engine instances;
- owned HAProxy identity, native configuration, route canary, and toggle arms;
- false-READY prevention for port collision and partial proxy state;
- revocation and exact first-cause classification after owned process loss; and
- bounded reverse-order cleanup with zero exact-generation survivors.

Pipeline-parallel checks bind stages to distinct physical hosts. Supervisor
fault checks kill the attested Ray head child and worker supervisor without
name matching and validate one FAILED terminal record for each.

## Residual constraints

- Ray's driver may emit GCS/task retry errors for up to its configured
  120-second reconnect timeout after catastrophic head/worker loss. Cleanup is
  bounded, but recovery is not advertised as instantaneous.
- Optional Ray metrics-exporter availability is not a readiness input.
- The scale study records controller pressure, actor-handle growth, proxy
  cliffs, shared-filesystem costs and streaming failures. Use those measurements
  as regression baselines when validating a new release.
- The no-delay on/off pair is a correctness/confound-control gate, not a
  throughput equivalence or large-scale performance claim.

## Revisit condition

Record the owner-selected scope for a packaged release, then declare and
execute its exact-candidate cells. Certifying additional release dimensions
requires the corresponding profile, evidence plan and review. The existing
256-node research evaluations remain the record of demonstrated system scale.
