# Known issues

**Role:** issue register. `hardening/FINDINGS.yaml` is the authoritative
disposition ledger; this file cannot close or waive a release gate. The measured
behaviour behind these entries, and what to do about it, is in the
[operations handbook](operations_handbook.md).

No artifact of the current tree is production-qualified
([hardening status](hardening/STATUS.md)). Large-scale observations below are
diagnostic context; they do not qualify the current architecture or establish a
support envelope.

## Current unresolved scale and scope observations

### A1. Envoy 256-node streaming deployment collapse — unqualified dimension

Three earlier Envoy streaming attempts reported zero request success after an
EngineCore port collision, unhealthy replicas, a Serve controller failure, a
false-ready marker, and later connection refusal. Envoy itself had initially
been healthy. Port ownership, false readiness, process ownership and failure
evidence are fixed for the HAProxy path, but Envoy, streaming and 256 nodes are
not an approved release dimension and have not been reproduced with the current
control plane; with the current control plane Envoy streaming already shows
connect-timeout errors at 64 nodes
([handbook](operations_handbook.md#5-gateways-clients-and-serving-settings)).
Ledger: `KI-A1`, `IN_PROGRESS`.

### A3. Ray GCS/controller pressure at large N — boundary evidence missing

Earlier 256-node runs showed roughly quadratic proxy and actor-handle work and
a single-controller bottleneck. ExaServe's readiness processing is indexed,
bounded, and does not poll the fleet, but it cannot remove or claim to solve
upstream Ray behaviour. Early deployments of one Serve application with a
replica on every GPU tile took about 100 s at 256 nodes, 199 s at 512 and
1,241 s at 1,024, about six times longer for the last doubling; at 2,048 nodes
(24,576 replicas) all three attempts reached the 1,200 s driver limit with
about half of the replicas running. Measure the current candidate at the
approved boundary tier before setting a larger supported maximum. Mechanism and
measurements: [handbook](operations_handbook.md#4-start-up-and-readiness).
Ledger: `KI-A3`, `IN_PROGRESS`.

### A7 / D2. Residual source-import and MPI activation cost — scale proof missing

Only the allocation head reads shared storage: source, generated overlay and
bootstrap are staged once into a node-local capsule, ranks import from it, and
every planned rank returns a receipt. The two-node gates prove both ranks
activated identical bytes. Only the native bootstrap has a syscall-level proof
of the non-head rule (two nodes); a trace of a real staged-model Ray and vLLM
run and per-rank shared-open counts at the approved scale are still required
([handbook](operations_handbook.md#3-stage-code-and-models)). Ledgers:
`KI-A7`, `KI-D2`, and `TD-COPPER`, `IN_PROGRESS`.

### B2. Centralized 256-node streaming congestion and rare HAProxy death

Bounded-client streaming through one head-node HAProxy plateaus at about 4.7
thousand requests/s from 128 nodes. At 256 nodes requests usually complete but
with a TCP retransmission storm (up to about 7 million retransmissions and about
200,000 established connections on the head node) and multi-second latency,
while the model servers stay healthy. About one in twelve ramp-ups instead ended
in total HAProxy death and connection refusal; its cause was not captured, and
the supervisor now records the gateway's exit code and signal. Do not conflate
the common degraded network regime with the rare process death
([handbook](operations_handbook.md#5-gateways-clients-and-serving-settings)).
Streaming is not a production claim. Ledger: `KI-B2`, `IN_PROGRESS`.

### D5. Pipeline-parallel patches fall back to a representative layer — fails closed in production

When no exact or canonical layer match exists, the pipeline-parallel
compatibility patches substitute the first layer of the type (backend and
model-layer lookup) or the first mapping entry (attention metadata), or skip a
KV-cache binding. These events used to appear only with
`EXASERVE_VLLM_PATCH_VERBOSE=1`, so a wrong-layer binding would not block READY.
The compiled plan now sets `EXASERVE_VLLM_PP_LAYER_FALLBACK`: production plans
(`fail`, also the behaviour when it is unset) stop the engine at the first
fallback and name the layer; validation plans (`record`) keep the substitution
and print one warning per layer to the engine's stderr
([_sitecustomize.py](../src/exaserve/_sitecustomize.py)). The warnings are not
yet part of the engine receipt, and the real PP=2 two-node canary has not been
rerun under the new policy, so it is not known whether that canary relies on a
fallback; if it does, production PP plans now fail at engine start. Rerun the
canary and read its stderr before claiming PP topologies or models, and use
canaries that check output correctness.

## Resolved mechanisms

### A2. Static port races — resolved

Ports are generation-owned through descriptor and lease contracts. An address
collision fails before the component counts toward readiness. A two-node null
gate deliberately held the HAProxy port and proved fail-before-launch behaviour.

### A4 / D1. False or proxy-only readiness — resolved

No log line, open socket, proxy health response, one canary, or prior-generation
file can make a deployment READY. The canonical predicate requires exact
sessions, resources, component, replica and engine receipts, owned gateway
state, and a typed completion through the advertised endpoint; it is
continuously re-evaluated. The two-node negative gate withholds a worker proxy
and remains non-ready. Scale support is tracked separately by `PR-033` rather
than by keeping the correctness defect open.

### A5. Tokenizer/Rayon oversubscription guard — resolved

The bounded tokenizer environment is a typed SiteProfile and compatibility
capability and is applied to the managed processes that need it, Ray actors
included. It is no longer an ambient shell workaround.

### A6. Scaling-trace ownership and load — resolved

Telemetry is deployment and generation scoped, bounded, freshness checked, and
owned by the composition lifecycle. Cleanup runs through the same bounded
shutdown path. Dead per-replica file-writing behaviour is not reachable.

### B1 / E1. Corrected non-streaming HAProxy result — preserved, not generalized

The corrected result is about 27.1k requests/s at 256 nodes with about 0.04%
errors and an explicitly bounded client topology. It replaced the confounded
result in which one client per node hammered a single proxy. This is regression
context, not scale qualification and not evidence about streaming
([handbook](operations_handbook.md#5-gateways-clients-and-serving-settings)).

### B3. LiteLLM fake streaming — resolved by typed timing semantics

LiteLLM's buffered end-burst cannot enter a real-streaming TBT comparison. The
result contract classifies it as `buffered_response`, retains throughput, error
and end-to-end evidence, and withholds TTFT and TBT. Only `incremental_sse` may
enter token-delivery SLO plots. Legacy results lacking the classification fail
closed rather than being inferred from plausible-looking fields. Ledger:
`KI-B3`, `FIXED`.

### B4. Over-context API error semantics — resolved

Earlier scale runs found that oversized non-stream requests returned HTTP 500
and streaming requests committed HTTP 200 before terminating the SSE body. The
server now counts the rendered prompt with the live backend tokenizer and
rejects prompt plus requested completion beyond `max_model_len` as a correlated
HTTP 400 before generation or headers. Ledger: `REL-API-01`, `FIXED`.

### B5. HAProxy thread count follows `gateway.worker_count` — resolved

The composition root used to pass `gateway.worker_count` to HAProxy as its
thread count. The shipped examples and the characterization specs set it to 1,
so HAProxy ran on one core, which cost 23% of streaming throughput at 64 nodes;
earlier measurements had used HAProxy's automatic thread count. A
`worker_count` above 1 still sets the thread count, but a value of 1 now leaves
it to HAProxy, and `gateway.options.nbthread` overrides both
([composition.py](../src/exaserve/composition.py)).

### C1. Server statistics silent/partial success — resolved

The active producer and consumer use one strict typed contract. Requested stats
must cover the planned producers; missing, malformed, or partial required stats
fail the run. The incompatible legacy pull API is not the production path.

### C2. Snapshot provenance — resolved

Run semantics and provenance are separate immutable identities. Dirty-tree
materialization requires explicit acknowledgement and records what was used;
submission cannot silently borrow current working-tree state.

### C3. Trailing bytes on structured rewrites — resolved

Structured state and results use same-directory temporary files, fsync where
required, and atomic replacement. Readers are strict and do not hide trailing
garbage with `raw_decode`.

### C4. Distributed result partials — resolved

Shard collection remains fault-isolating rather than reverting to the hanging
root collective, but exact rank and result identities and terminal completeness
are mandatory. A missing or duplicated shard cannot produce success.

### C5. Client topology footgun — resolved

For `dest=proxy`, one client rank per deployment node aims the whole fleet at
one front proxy; at 256 nodes that was misread as a proxy throughput regression
(see B1). The bounded default of four client nodes did not reach YAML specs:
the loader filled an omitted `client.num_nodes` with the deployment node count,
and matrix expansion overwrote even an explicit value unless the matrix
targeted or derived it. An omitted count is now kept as "derived" and
recomputed for every matrix variant (at most four nodes for proxy runs, one per
node for direct runs, one for saturation searches); an explicit or derived
value is kept as written, and a negative one is rejected. The tests go through
the YAML loader and matrix expansion
([test_spec_footguns.py](../eval/tests/test_spec_footguns.py)). Proxy results
from earlier specs that did not target or derive the count used one client
rank per deployment node, whatever the spec said. Ledger: `KI-C5` (plan
contract).

### C6. TTFT/TBT interpretation — resolved

Analysis and figures report TTFT and TBT only for `incremental_sse` timing.
Non-streaming and buffered runs retain end-to-end latency but cannot populate or
enter token-delivery fields and SLO panels.

### D3. Competing proxy instrumentation owner — resolved

The retired profiling hook and full-file overlay path are absent from the
reachable production code. Instrumentation has one documented owner and atomic
activation and receipt semantics.

### D4. Pipeline-parallel topology/private API — resolved for selected profile

PP topology is a plan capability with explicit node-pinned stage ownership. One
real PP=2 replica across two physical hosts was proven with exact EngineCore and
worker receipts. Unsupported multi-replica and non-shard combinations fail plan
capability checks rather than proceeding with ambiguous placement; see D5 for
layer-name fallbacks.

## Lessons kept from retired branches

These issues recurred during development on branches that are not published
([retired branches](path_migrations.md#retired-branches)). The summaries keep
the lessons from the branch audit; the findings ledger does not track them
separately.

### L1. Ray Serve request-router crash loop when queue-length probes time out — mitigated

At 64 or more nodes (768 or more single-tile replicas) with saturated
replicas, every queue-length probe from Ray Serve's request router missed the
default 0.1 s deadline at once, and the router then failed in a loop with
`AttributeError: 'NoneType' object has no attribute 'routing_context'`: Ray's
backoff path reaches that check with no pending request when routing tasks
outnumber queued requests. Raising the deadline removed the crash. The Aurora
site profile sets `RAY_SERVE_QUEUE_LENGTH_RESPONSE_DEADLINE_S=300.0` before any
Ray process starts ([site.py](../src/exaserve/site.py)); keep it, and repeat a
saturated 64-node run before lowering or removing it.

### L2. Control reconnect grace shorter than the start-up burst — default raised

At 16 and at 64 nodes the synchronized engine start-up burst outlasted the
default 60 s control reconnect grace: rank control sessions that dropped during
the burst could not reconnect in time, and the deployment failed closed before
READY; 300 s recovered every rank at 16 nodes. The plan compiler now uses 300 s
for deployments of 16 nodes or more
([compiler.py](../src/exaserve/plan/compiler.py)); an explicit
`deployment.control.reconnect_grace_s` still wins. The cost is slower failure
detection: a rank that does not come back is declared lost 300 s after its
session drops, not 60 s. The raised default has not been run at scale yet. The 64-node attempts also needed transport and
event-store fixes that are now in the code (a socket reset while writing a
heartbeat response is treated as a recoverable rank loss, and receipt batches
survive reconnects).

### L3. Lmod is not `nounset`-clean — resolved

Job scripts that enabled `set -u` before sourcing the site environment failed
inside Lmod with an unbound-variable error (`ZSH_EVAL_CONTEXT`); this recurred
three times. Job bodies rendered by ExaServe enable `set -u` only after the site
bootstrap ([schedulers/base.py](../src/exaserve/schedulers/base.py)); hand-written
setup scripts need the same order.

### L4. Outbound HTTP proxy intercepts allocation-internal requests — resolved

Compute-node environments export an outbound HTTP proxy whose `no_proxy` list
does not cover node addresses or numeric loopback, so health checks, canaries
and replay requests made with standard HTTP clients went to the proxy and
failed; this recurred at least four times. Every internal HTTP client
(composition root, node supervisor, readiness checks, replay engine, ClientLab)
now uses a direct opener that ignores proxy variables; new internal clients must
do the same.

### L5. Worker-node logs lost when collected at job teardown — resolved

Copying Ray session logs and node-local instrumentation from worker nodes after
the launcher exited repeatedly returned empty or partial results at 32 to 64
nodes. Nodes stopped answering while the scheduler tore the job down and
cleaned node-local scratch, Ray session directories could disappear once
shutdown began, remote-glob copies returned nothing without an error, archiving
live Ray log directories hung on sockets and files still being written, and a
timeout wrapper killed copy jobs it did not own. Each rank now archives its own
node-local diagnostics after its Ray child has stopped, in a bounded, killable
subprocess that skips links and non-regular files and records how many it
skipped ([state/diagnostics.py](../src/exaserve/state/diagnostics.py), called
from [rank_main.py](../src/exaserve/rank_main.py)). A diagnostics failure is
reported but never changes the run outcome; new collectors should gather in
band before the job step ends.

## Current release blockers

- ADR-000's proposed 64-node ceiling needs a product-owner decision; and
- if 64 is selected, exact-candidate 4/16/64 qualification remains required.

See the [hardening status](hardening/STATUS.md) and the
[compatibility matrix](hardening/COMPATIBILITY_MATRIX.md) for the current
release verdict.
