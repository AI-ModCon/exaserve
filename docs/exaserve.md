# ExaServe reference card — hardened architecture

This page is the machine-readable companion to `ExaServe_Reference_Card.docx`.
The authoritative architecture and acceptance contract is
[`PRODUCTION_HARDENING_EXECUTION_PLAN.md`](PRODUCTION_HARDENING_EXECUTION_PLAN.md);
the live release verdict is [`hardening/STATUS.md`](hardening/STATUS.md).

## Demonstrated scale and reference runtime

ExaServe has been evaluated on **up to 256 Aurora nodes**, including
HAProxy-fronted Llama-3-8B inference and pipeline-parallel Llama-3.1-405B
serving, on earlier snapshots of this code; the current tree has not been
re-measured at that scale. The [paper](https://arxiv.org/abs/2609.10812) and
[operations handbook](operations_handbook.md) describe the workloads, measured
throughput, gateway behaviour and limits.

The reference deployment uses:

- ALCF Aurora, native PBS;
- Intel PVC/XPU, 12 accelerator tiles per node;
- vLLM under the exact compatibility profile of Aurora frameworks/2025.3.1;
- HAProxy on the allocation head;
- non-streaming OpenAI-compatible requests; and
- trusted allocation-internal network exposure.

Fix-specific regression coverage is recorded in the
[changelog](../CHANGELOG.md#validation-coverage). It does not reduce the
system's demonstrated 256-node scale. No artifact of the current tree is
production-qualified: production plans compile to at most two nodes, and
production submission fails closed. Formal production-release admission
remains a separate, artifact-specific process in the
[hardening status](hardening/STATUS.md).

Slurm/PSI-J, CUDA/ROCm, SGLang, streaming, public exposure, direct Serve
exposure, and LiteLLM/NGINX/Envoy/Pingora are unsupported or validation-only.
The presence of an implementation interface is not a support claim.

## Run

Use the operator-provisioned site interpreter and ExaServe artifact described
in [getting started](getting_started.md#aurora-development-and-serving).
Job isolation disables user-site packages, so installing only with `--user`
does not provision the serving runtime. Load the profiled stack as
[Prepare the runtime](getting_started.md#prepare-the-runtime) shows (the
default `frameworks` module fails the compatibility check), then check the
selected environment:

```bash
PYTHONNOUSERSITE=1 PYTHONSAFEPATH=1 python3 -c 'import sys, exaserve; print(sys.executable); print(exaserve.__file__)'
command -v mpiexec
command -v haproxy
```

The following compact example uses two nodes for readability. Select an
authorized validation configuration or an admitted release profile before
submission; the current default profile fails production admission closed.

```bash
cp examples/config.haproxy.yaml my_config.yaml
# Edit model_storage_path.
# The job sources this site environment script; submission requires it.
export EXASERVE_ENV_SCRIPT_AURORA=/absolute/path/to/environment.sh
# The site profile derives its model-storage root from this, even when the YAML sets model_storage_path.
export EXASERVE_PROJECT_ROOT=/lus/flare/projects/YOUR_PROJECT
exaserve-serve-submit my_config.yaml --project-account YOUR_PROJECT --wait
```

The submit command prints the exact job ID. It prints an endpoint only after the
matching deployment generation publishes canonical `READY`; PBS `RUNNING`, an
open proxy socket, or stdout text is insufficient.

```bash
exaserve-serve-url JOB_ID --wait
exaserve-status show --run-dir /path/to/run --json
qdel JOB_ID
```

## Canonical deployment input

```yaml
num_nodes: 2
num_gpus_per_node: 12
node_cpus: 64
ray_port: 6379
model_storage_path: /lus/flare/projects/PROJECT/USER/models
local_stage_path: /tmp/hf_home
deployment_name: exaserve_serve
replica_max_ongoing_requests: 32
engine: vllm
vendor: xpu

models:
  - model_id: meta-llama/Meta-Llama-3-8B-Instruct
    tensor_parallel_size: 1
    pipeline_parallel_size: 1
    max_model_len: 4096
    size: 8
    gpu_memory_utilization: 0.90
    enforce_eager: true
    max_num_seqs: 64
    num_cpus_per_replica: 4

exposure:
  mode: PROXIED_INTERNAL
  network_boundary: trusted_allocation

gateway:
  kind: haproxy
  port: 4001
  backend_port: 8000
  executable_ref: PATH:haproxy
  worker_count: 1
  options:
    balance: leastconn
    maxconn: 8000
```

There is no nested `model_deployment_config`, `proxy_config`, or mutable Ray
runtime schema. `maxconn: 8000` is a conservative default; ExaServe
calculates and checks the exact required `RLIMIT_NOFILE` before HAProxy launch
(Aurora compute nodes allowed 1,048,575 descriptors when measured).

## What the control plane proves

One Python composition root owns the complete generation. It persists immutable
plan/site/allocation identities, runs finite staging, supervises all process
groups, hosts the authenticated rank-control sessions, owns the deployment
child and HAProxy, evaluates readiness, and performs bounded cleanup.

`READY` requires the exact planned node sessions, Ray membership/resources,
Serve applications and replicas, engine/process compatibility receipts, route
health, the owned gateway, and a real canary through the compiled advertised
endpoint. Evidence is generation-bound and freshness-limited. Loss after READY
revokes readiness and triggers the declared failure/teardown policy.

Subprocesses exist only at genuine OS boundaries and use argv vectors,
deadlines, process-group ownership, and structured handshakes. No shell wrapper
or output parser decides lifecycle or readiness. Compatibility uses targeted,
version-pinned activation with attestation; the old full-file overlay/replacement
path was removed.

## Eval and ClientLab

Set `EXASERVE_PROJECT_ROOT`, and for materialization and submission also
`EXASERVE_PROJECT_ACCOUNT` and `EXASERVE_ENV_SCRIPT_AURORA`, as in
[getting started](getting_started.md#configure-evaluation-environment-preparation);
even `spec validate` needs the project root. Run from the repository root
(the eval tooling imports ExaServe from the checkout's `src/`), and replace
`run0` with the `runN` group in the `run.yaml` paths that `run materialize`
printed. Run ClientLab `run` and `smoke` studies in a compute session
([AGENTS.md](../AGENTS.md)).

```bash
export PYTHONPATH="$PWD:$PWD/src"
python3 -m eval.cli spec validate eval/specs/smoke_haproxy_1node.yaml
python3 -m eval.cli run materialize eval/specs/smoke_haproxy_1node.yaml
python3 -m eval.cli run submit-all smoke_haproxy_1node --run-group run0

python3 -m clientlab plan client_microbench
python3 -m clientlab smoke client_microbench
```

Eval embeds the exact DeploymentPlan inside one immutable RunPlan and requires a
complete result manifest. ClientLab synthetic results are diagnostic-only; a
real deployment study must bind its RunPlan, trace, generation, and status
directory. Neither subsystem owns a private scheduler, serving lifecycle, or
readiness protocol.

## Measured scaling

Scale evaluations reached 256 Aurora nodes with HAProxy/non-streaming and
pipeline-parallel workloads, on earlier snapshots of this code. Their results
and lessons are summarized in the [operations handbook](operations_handbook.md);
original records remain in the repository history. These measurements establish
the system's demonstrated research scale; they are not release evidence for the
current tree. Verification of subsequent changes is recorded separately in the
changelog, and release admission binds a particular artifact and profile.

## Regenerating the Word reference card

`docs/ExaServe_Reference_Card.docx` is generated output. It embeds the two
measurement figures and the Academy template's styles, but the repository does
not track the template or the figure files, so a clean clone needs these ignored
inputs restored first:

```text
tmp/ref_card/Academy_Framework_Reference_Card.docx
docs/figures/fig1_proxy_scaling.png
docs/figures/fig7_pp405b.png
```

The two figures are Figs. 2 and 5 of the
[ExaServe paper](https://arxiv.org/abs/2609.10812), rasterized from its arXiv
source with `pdftoppm -r 220 -png -singlefile`. Three points of Fig. 5 come
from runs that were later excluded because they attached the deployment to a
256-node Ray cluster: HAProxy at 32 and 64 nodes and direct dispatch at 64
nodes. The card's text uses the corrected values in
`eval/plot/pp405b_legacy_evidence.yaml`, and the figure's caption says so. The
template is not distributed with ExaServe or with the public Academy
repository; ask the Academy maintainers for it. From any working directory,
run:

```bash
python3 /path/to/exaserve/tools/make_refcard_docx.py
```

The generator resolves all paths relative to its repository, verifies the PNG
inputs, and atomically replaces the generated DOCX. Edit the generator and
this Markdown companion rather than editing generated Word XML by hand.
