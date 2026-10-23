# Deployment and operations handbook

This handbook collects what development and hardware validation on Aurora
taught about deploying and measuring ExaServe: prerequisites that are easy to
miss, behaviour at scale, failures that have been seen and how they were
handled, settings that worked, and measurement and evidence practices. It
replaces the run logs, audits and research notes kept during development; those
records remain in the repository history.

Read it together with the [hardening status](hardening/STATUS.md), which says
what the current tree is qualified for (no production-qualified artifact
exists), the [known issues](KNOWN_ISSUES.md), and the
[compatibility matrix](hardening/COMPATIBILITY_MATRIX.md).

Unless a section says otherwise, numbers come from Aurora (Intel PVC, 12 tiles
per node) with Ray 2.53.0, vLLM 0.15.0 and Llama-3-8B with one replica per tile.
The scale evaluations reached **256 Aurora nodes**. They were measured on
earlier snapshots of this code, often in validation mode: use them for sizing
and as regression baselines, not as qualification of the current tree.
Verification of later fixes is recorded separately in the
[changelog](../CHANGELOG.md#validation-coverage); packaged-release admission is
tracked in the hardening status.

**Contents**

1. [Prepare the site and the job environment](#1-prepare-the-site-and-the-job-environment)
2. [Plan the allocation](#2-plan-the-allocation)
3. [Stage code and models](#3-stage-code-and-models)
4. [Start-up and readiness](#4-start-up-and-readiness)
5. [Gateways, clients and serving settings](#5-gateways-clients-and-serving-settings)
6. [Failures, recovery and shutdown](#6-failures-recovery-and-shutdown)
7. [Measuring correctly](#7-measuring-correctly)
8. [Qualification and evidence](#8-qualification-and-evidence)
9. [Engineering rules for contributors](#9-engineering-rules-for-contributors)
10. [Open problems](#10-open-problems)

## 1. Prepare the site and the job environment

**Use the site runtime exactly as profiled.** The serving stack comes from
Aurora's `frameworks/2025.3.1` module (Python 3.12, Ray 2.53.0, vLLM 0.15.0+xpu,
mpi4py 4.1.1), loaded from the 26.26.0 image's module tree with the recipe in
[getting started](getting_started.md#prepare-the-runtime); the default
`frameworks` module (2026.1.0) fails the compatibility check. Go comes from the
go module. In every session load both, unset `ONEAPI_DEVICE_SELECTOR`, and
compare module versions with the compatibility profile before a campaign. The
profile pins Python, Ray, vLLM and mpi4py and fails closed on a mismatch: a
changed module is a new profile that needs new hardware evidence, never a
bypass. Do not depend on host tools that the job environment does not declare.

**Import MPI only through `exaserve.mpi_loader`.** On Aurora's current default
image the OS libssl needs symbols (`OPENSSL_3.0.1`) that the frameworks stack's
own libcrypto lacks. MPICH links libcurl and lists `/usr/lib64` in an RPATH
that outranks `LD_LIBRARY_PATH`, so a process that has loaded `hashlib` and
then imports mpi4py fails with "version `OPENSSL_3.0.1' not found"; source
staging died this way before any rank started. `import_mpi()` imports `ssl`
first, so the process keeps one OpenSSL, and a test rejects any other mpi4py
import. Staging ranks run with an explicit environment, so a site-level
preload cannot reach them.

**Device selection on Aurora.** Device visibility comes from the plan through
`ZE_AFFINITY_MASK`. Never introduce `ONEAPI_DEVICE_SELECTOR`: the site profile
unsets it and sets `RAY_EXPERIMENTAL_NOSET_ONEAPI_DEVICE_SELECTOR=1`, because
Triton's SYCL probe crashes when Ray rewrites the selector to a `level_zero`
list. Ray's GPU count also comes from the plan, not from a site constant.

**Isolate Python from the user site.** On Aurora the home directory is on the
shared Lustre filesystem, and the framework Python has user site-packages
enabled, so `~/.local/.../site-packages/{sitecustomize,usercustomize}.py` load
into every interpreter (one such hook once replaced `builtins.__import__` and
changed Ray Serve timeouts). Before a first deployment, look for those files.
Export `PYTHONNOUSERSITE=1` and `PYTHONSAFEPATH=1` before the first Python
process of a job; the launcher refuses to start without them, and actor
runtimes check again. Never install ExaServe with `pip --user`.

**Job body order.** Lmod reads shell variables that are legitimately unset, so
a body that enables `set -u` before sourcing the site environment dies inside
Lmod. Rendered bodies therefore run `set -eo pipefail`, unset virtual-environment
variables, export the Python isolation variables, source the site script,
export them again, unset `ONEAPI_DEVICE_SELECTOR`, then enable `set -u` and exec
one Python entry point. Hand-written scripts need the same order (see
[L3](KNOWN_ISSUES.md#l3-lmod-is-not-nounset-clean--resolved)). The site
environment script and `bootstrap_script` are privileged operator code; never
pass untrusted text through them.

**Keep the site adapter thin.** A scheduler adapter may only select the
interpreter, load unavoidable modules, validate the allocation, sanitize the
inherited environment and end in exactly one exec of the launcher. Staging,
rank launch, gateway, readiness, collection and cleanup belong to the
composition root. Start ranks through the scheduler's own launcher, never SSH:
an SSH session loses the allocation context and process ownership, and on
Aurora's Slingshot fabric `mpiexec` from an SSH session fails with
`VNI request failed [409]: Failed to find specified job`. A Slurm or other-site
adapter must re-prove environment propagation, worker-exit aggregation and
process-tree cleanup.

**Close the rank environment, including HOME.** `mpiexec` otherwise forwards
the head's environment, working directory and scheduler state. PMIx reads
`$HOME/.pmix` during initialization, before application code runs, so a worker
rank with an inherited Lustre HOME touches shared storage even when everything
else is clean. ExaServe launches with
`mpiexec --genvnone --envnone --envlist <names> --wdir <node-local dir>`, gives
pre-capsule ranks `HOME=/tmp` and `TMPDIR=/tmp`, and passes only the PMIx
settings named in the site profile. On a new site, find every library that
reads HOME or a cache directory before `main()` (PMIx, MPI, fabric providers),
pin it in the site profile, and confirm with a syscall trace on a non-head rank.

**Declare and verify filesystem roots.** The site profile declares shared,
node-local and read-only site roots with filesystem type and read-only state;
the head verifies the shared roots and every rank verifies its local roots and
the read-only site Python. On Aurora, `/home` and `/lus/flare` are shared
Lustre, `/tmp` is node-local tmpfs, and the frameworks image under `/opt/aurora`
is read-only squashfs. Measure these on a compute node: login-node mounts
differ, a path that exists on every node is not thereby node-local, a `/tmp`
spelling can be a symlink, and an image can have a shared backing store. The
interpreter must sit under a declared read-only site root; a virtual environment
in the home directory fails.

**Unix socket paths have 107 bytes.** vLLM appends 37 bytes to its RPC base
path and Ray appends `ray/session_<timestamp>_<pid>/sockets/<name>` to
`RAY_TMPDIR`. A real canary once failed because a long temporary base produced
a 123-byte ZMQ path. ExaServe derives a fixed-length node-local state root and
validates `VLLM_RPC_BASE_PATH` before importing vLLM (worst case 85 bytes).
Budget every socket-bearing directory against the limit before relocating
runtime roots, and keep them off long scheduler-provided temporary paths and
off shared storage.

**One network identity per node.** Ray, vLLM, gateway backends and receipts
must use the same fabric address: Serve binds its proxy to the Ray node IP (a
request to the scheduler hostname returned 503), and an implicit `VLLM_HOST_IP`
let vLLM pick a second address and fail its one-IP-per-node check. Every Ray
daemon therefore inherits `VLLM_HOST_IP` equal to `--node-ip-address`. Compare
host names in canonical form (the nodefile holds fully qualified names while
processes report short ones). Compute nodes export `http_proxy`, so internal
HTTP clients ignore proxy variables
([L4](KNOWN_ISSUES.md#l4-outbound-http-proxy-intercepts-allocation-internal-requests--resolved)).
The worker fabric address is resolved through an Aurora DNS suffix in
`src/exaserve/control/ray_runtime.py`; a new site needs that in its profile.

**Expect leftovers on reused nodes.** A generation killed before `ray stop`
leaves its session name behind, and the next `ray start --head` fails with a
message that looks like a Redis error ("Session name ... does not match
persisted value"). `ray stop` does not reap the engine children that replicas
spawn, and those keep device memory. ExaServe gives every generation its own
`RAY_TMPDIR` and reaps only process groups it owns from strictly older
generations of the same deployment. Never kill by process name or by user,
never reuse a Ray session directory, and check for orphaned engine processes
when device memory is unexpectedly in use.

**Security posture.** There is no authentication or TLS on the serving
surface. HAProxy, every node's Serve proxy and Ray's ports listen on all
interfaces, and anyone who can reach Ray's ports can run code as the job user,
so deploy only where the site network restricts the allocation to trusted
users ([SECURITY.md](../SECURITY.md#deployment-trust-assumptions)). Treat model
directories (weights, configuration, tokenizer) as code and keep the model
store writable only by the operator. The HAProxy statistics page is read-only
on loopback by default and the compiler rejects an administrative or
non-loopback statistics page; secret-bearing gateway options accept only
`{secret_ref: ...}` references. The head-to-rank control channel is
authenticated with a per-deployment secret that travels only in the job
environment and is stripped from Ray, Serve, engine and probe children; with a
new launcher, prove the secret reaches each rank only that way.

## 2. Plan the allocation

**Size walltime from measured cold-start time, not from queue defaults.**
Default queues are capacity for 1-16 nodes (one hour), debug-scaling for 17-255
nodes (one hour, the site maximum) and prod from 256 nodes (two hours); the
defaults never widen the support envelope. Large models do not fit those
defaults:

| Deployment | Measured cold start |
|---|---|
| Llama-3.1-405B, TP=8 x PP=2, one replica per two nodes | head-side model verification (a full hash of the shared copy) 13-16 min; complete model staging, including that verification, 47-53 min; READY 57-64 min after start at 4, 8 and 256 nodes; whole jobs 61-76 min |
| Llama-3-8B, TP=1, 12 replicas per node (earlier direct-routing path) | weights broadcast (about 30 GiB) 47-49 s, flat from 2 to 64 nodes; READY about 100 s at 2 nodes, 200-260 s at 16, 300 s at 64 |
| Llama-3-8B, TP=8 x PP=2 on two nodes | READY about 430 s, most of it engine creation |
| Null compute (no model), HAProxy, 12 replicas per node | READY 29-30 s at 32 nodes, about 40 s at 64 nodes and 549-555 s at 256 nodes |

Request at least about 90 minutes for any cold 405B run, even at four nodes.
405B specs request two hours below 256 nodes and four from 256.
At 17-255 nodes that exceeds the one-hour debug-scaling limit, so `submit` and
`submit-all` refuse those cells before contacting the scheduler and leave them
PLANNED; run them as allocation-campaign children (below).
Node-local tmpfs is wiped at job end, so every allocation pays the staging cost
again. Record per-stage transfer times in every large-model run; in one 8-node
405B run stage 0 moved data about three times slower than stage 1, and the
cause is not established.

**Middle scales.** Where no exact-size queue fits (for 405B on Aurora, 32-128
nodes), a finite allocation campaign runs immutable child runs one at a time on
exact node subsets of one larger allocation
(`python3 -m eval.cli allocation materialize|submit|execute`). The native batch
head stays the only controller and shared-filesystem reader, each child gets a
reserved 900 s cleanup window, and any failure stops the sequence. The
controller in the current tree records its bootstrap (account, environment
script, spool) in schema 2 and has not been re-proven on hardware; it needs a
new four-physical, two-logical-node proof before production use. Keep the
over-launch test in any subset mechanism: launching one rank more than the
nodefile holds must fail ("Cannot place all ranks on node list") without
starting extra ranks. Report physical and logical node counts separately.

**Submission is idempotent; ambiguity is not permission to resubmit.**
Submission writes a durable intent before calling the scheduler. A scheduler
timeout raises an ambiguous-submission error, and the same command run again
reconciles with the exact job instead of submitting a second one; use
`--new-generation` only to start a new deployment on purpose. A failed queue or
job query is UNKNOWN, never "empty" or "finished". `submit-all` keeps one job
per queue in flight by default, holds while queue counts cannot be observed,
retries a definite rejection at most 20 times, polls every 300 s and gives up
after 12 hours of queue wait.

## 3. Stage code and models

**One shared-filesystem reader per allocation.** Only the allocation head,
proven as MPI global rank 0, may read or write shared storage during a run.
Source, plan, site and binding data, compatibility content and native helpers
go into a content-addressed capsule published to node-local `/tmp`; ranks,
actors and replicas read only from it; per-rank results return by MPI gather
or the authenticated control channel and only the head writes shared
artifacts. Treat this as a correctness rule, not tuning: before it was
enforced, one 256-node start-up succeeded and a repeat of the same snapshot
failed before START, because thousands of processes re-opened shared files.
Anything that runs per replica multiplies its opens and hashes by the replica
count (at 256 nodes, re-reading one 2.4 MB plan in every replica came to about
7 GB of reads). Any new tool, collector or cache must read from the node-local
capsule; a run that succeeds while the filesystem is quiet proves nothing.

**Model staging.** One allocation-wide broadcast rooted at global rank 0 streams
each file once to the ranks that need it; each pipeline stage receives only its
shards. `local_stage_path` must be on a declared node-local root, never shared
storage (single-replica PP specs once pointed it at the Lustre model path, so
vLLM read weights from Lustre). Model identity is a full SHA-256 of every byte,
so every launch re-hashes the model from the shared store; budget for it. A
model collective that cannot finish within 1,800 s fails the staging step. The
shard partition must match vLLM's `get_pp_indices`.

**Completeness and integrity.** A model directory counts as complete only when
its completion manifest lists every file with a full hash and the source
revision; downloads run under a renewed lease into a sibling directory and are
published atomically. A "partial or corrupt model directory ... Refusing to
overwrite it" error needs manual inspection and removal, and quarantined
`.invalid.` trees in the model store need manual cleanup; never hand-write
`.exaserve_complete.json`. A pre-existing directory without a marker passes on
structural checks only, so stage models through ExaServe. Locality checks
resolve every path component without following symlinks and detect nested
mounts from the kernel's mount table (a `/tmp` model directory whose weight
files were symlinks into Lustre once passed a top-level check, and `st_dev`
comparisons missed nested overlay mounts). There is no fallback that loads a
model by name when staging evidence is missing, and the Hugging Face offline
variables are forced; do not add either back.

**vLLM model-info seeds.** vLLM 0.15's model-registry subprocess crashes
(SIGSEGV) on a cold cache when it imports the XPU model classes. Reviewed
model-info seeds ship with ExaServe and are installed into each generation's
node-local cache, and the head checks every model's `config.json` against the
reviewed set before broadcasting. A new architecture or a vLLM rebuild needs a
reviewed seed and new real-engine evidence; do not point workers at a shared
home cache to work around the crash.

**Source staging.** The head assembles the capsule in head-local `/tmp`, the
broadcast helper is copied to workers with PALS `--transfer` (request it
explicitly; the default is not a contract), rank 0 alone reads the source, and
publication replaces the tree atomically and freezes it read-only. After the
change, source staging took 4-6 s for about 415 files (23-25 MB) from 4 to 256
nodes, where per-rank result files on Lustre had once made the same stage take
44 s at 256 nodes. A fast payload inside a slow stage means the metadata I/O
around it is the bottleneck. Stage every per-node artifact a remote process
needs on that node, never only on the head.

**Shutdown diagnostics.** Per-rank diagnostic archives (at most 64 MiB) stay
node-local and only a bounded summary crosses the control channel; node-local
data disappears with the allocation, so gather what you need in band before the
job step ends ([L5](KNOWN_ISSUES.md#l5-worker-node-logs-lost-when-collected-at-job-teardown--resolved)).

## 4. Start-up and readiness

**READY comes only from ExaServe's status record.** The readiness coordinator
evaluates READY against the compiled plan and allocation binding: exact rank
sessions, Ray membership and resources, planned Serve applications and
replicas, exact compatibility receipts, owned gateway health, and one real
completion per model through the advertised endpoint. Read it with
`exaserve.status_api` or `exaserve-status` for the expected generation and plan
hash. Never infer readiness from a log line, a running scheduler job, an open
port, `/health`, Ray return values or the newest file. Ray Serve's own status
lags: an application reported RUNNING while routes still returned 502 for two
seconds, and a killed replica stayed RUNNING for about 120 s. READY is
re-evaluated every 5 s and can be revoked (VALIDATING) and re-granted, so
clients must tolerate it.

**Fixed start-up costs.** Every new Ray process waits about 30 s for Ray's
metrics agent (compile-time retry constants; disabling metrics collection does
not remove it), so Serve start-up takes 35-47 s at any size. Engine creation
for an 8B model took about 33 s (weights about 18 s). Never set a Ray-side
ready or health timeout below about 60 s.

**Ray Serve start-up grows super-linearly with node count.** In instrumented
runs on an early (April 2026) snapshot, with one deployment of N replicas, the
wait for every node's proxy grew about 4.5x per doubling (22, 94, 394 and 1,752 s at 32, 64, 128 and 256 nodes). On every
replica-set broadcast, each proxy re-resolves every replica's actor handle, so
cluster-wide lookups grow with nodes squared (786,000 lookups per broadcast at
256 nodes); at 128 nodes the slowest proxy's lookup time matched the wait to
within 0.4%. No ExaServe change removes this; it needs an upstream Ray Serve
change. The current tree deploys a dense HAProxy model as one application with
every replica plus per-node proxy anchors; the other layouts are listed under
"Serve application count dominates bring-up" below. None of them has been
re-measured at scale.

**Ray's proxy health checks kill busy proxies.** The stock proxy ready check
(5 s, three failures) is shorter than the 30 s start-up wait above, and busy
controller and proxy event loops make health checks time out while TCP round
trips stay at milliseconds; from 64 nodes most worker proxies were killed and
restarted, and with a real model at 256 nodes the controller killed 74 proxies.
At 64 nodes all proxy health checks once expired together at 300 s while the
controller was still reconciling healthy applications, and Ray 2.53 then
asserted in asyncio `_chain_future` once per proxy (fixed by patch RS-03, which
must be active in both the deployment and Ray-head roles because the Serve
controller inherits the head raylet's environment).
The current tree sets `RAY_SERVE_PROXY_READY_CHECK_TIMEOUT_S=60` and a proxy
health-check timeout at least as long as `readiness.initial_deadline_s`
(default 3,600 s), and checks them before connecting to Ray. Treat Ray's proxy
health checks as a watchdog, never as readiness. Replica health-check timeouts
are the earliest sign that the controller is falling behind.

**Throughput-optimized Serve couples proxy liveness to router work.**
`RAY_SERVE_THROUGHPUT_OPTIMIZED=1` (set by the site profile) also turns off
`RAY_SERVE_RUN_ROUTER_IN_SEPARATE_LOOP`, so router updates run on the loop that
answers the proxy's readiness and health calls. If proxy health stalls at
scale, test `RAY_SERVE_RUN_ROUTER_IN_SEPARATE_LOOP=1` first; it has not been
tried.

**The Serve controller stalls as replicas grow.** Its single event loop showed
reconcile ticks of up to 1.0, 2.1 and 4.3 s at 32, 64 and 128 nodes, and
confirming replicas after model load took 0.3, 2.6 and 66.8 s at 8, 32 and 64
nodes. Keep extra controller calls (such as fleet-wide status polling) off the
start-up path; ExaServe reads the long-poll stream instead.

**Proxies start late, and only where a replica runs.** Ray Serve creates a
worker-node proxy only after the controller has seen a replica on that node,
about 40 s into the deploy at every scale. ExaServe pins a route-less anchor
application to every planned node so every node gets a proxy; do not rely on
`EveryNode` alone.

**Serve application count dominates bring-up.** Ray's Serve controller
confirms applications one after another. With one application per replica at
64 nodes (832 applications), backend bring-up took 690-733 s although all 768
replicas were healthy after about 81 s; the single-application layout took
82-139 s at the same scale. Dense HAProxy plans (one model, TP=1, PP=1, a
replica on every device) therefore compile to one Serve application plus
per-node proxy anchors, and dense null-compute plans to one node-pinned
application per node. Envoy, LiteLLM, direct, sparse, multi-device,
pipeline-parallel and multi-model plans still use one application per replica:
budget 10-12 minutes of Serve reconciliation at 64 nodes for them, and 9-10
minutes of control-plane start-up at 256 nodes in any layout.

**With one Serve application per node (the paper's layout), one Ray cluster
reached about 256 nodes.** At 256 nodes (3,072 replicas) the
serve stage took about 30 minutes and varied widely; at 512 nodes raylets on
many nodes failed with "Failed to get cluster ID from GCS server" and the
deploy failed. The current tree raises the GCS bootstrap budgets (connect
timeout 30 s, reconnect 120 s, worker registration 120 s, 8 GCS server
threads, a 60 s request timeout) and proves they reached a fresh remote worker
before deploying. Whether that lifts the 512-node failure is untested. Do not
plan one Ray cluster beyond 256 nodes without a new boundary measurement, and
give a 256-node start-up at least an hour. Start-up-only results of a
single-application layout beyond 256 nodes are recorded under
[known issue A3](KNOWN_ISSUES.md).

**Thread limits at 128 nodes and above.** Each replica holds about 1,500 gRPC
connections, and the Hugging Face tokenizer lazily builds a thread pool of
about one thread per core on the first request, which failed with
`ThreadPoolBuildError ... WouldBlock` and `GlobalPoolAlreadyInitialized`.
`RAYON_NUM_THREADS=1`, `TOKENIZERS_PARALLELISM=false` and Ray's gRPC thread
clamps are set in every managed process, Ray actors included; keep them.

**Head-side persistence must not block the control loop.** At 256 nodes one
fsync-heavy event file per receipt binding on Lustre, written under a lock that
the listener's event loop also waited on, delayed heartbeats until 75 ranks
timed out before START. Receipt events are now group-committed on a dedicated
writer thread. No event-loop thread may wait on a lock that is held across
filesystem I/O; test heartbeat latency under a deliberately slow store before
trusting a new persistence path at scale.

**Control-channel deadlines are unmeasured candidates.** Defaults:
registration 300 s, reconnect grace 60 s (300 s from 16 nodes), heartbeat 5 s,
lease timeout 30 s (at least three heartbeats is enforced), watchdog cleanup
300 s, frames at most 1 MiB. Environment variables cannot override compiled
values. At 16 nodes eight rank sessions dropped during the synchronized engine
start-up and could not reconnect within 60 s, and `reconnect_grace_s: 300`
recovered all of them; the compiler therefore raises the default from 16 nodes
([L2](KNOWN_ISSUES.md#l2-control-reconnect-grace-shorter-than-the-start-up-burst--default-raised)),
and an explicit `deployment.control` value still wins. A rank that never
returns is then declared lost after 300 s rather than 60 s. Record the measured
values per tier.

**Ports.** Twelve replicas starting at once on a node used to pick the same
free port (EADDRINUSE). Engine ports now come from node-local exclusive leases
held until the engine binds, and the gateway listener is bound before staging
and handed to HAProxy, so a gateway port conflict fails within seconds. A
foreign process can still take a port between probe and bind; keep unrelated
listeners out of the engine port windows (23000 + 100 x device).

**Compatibility patches.** Any Python, Ray, vLLM, frameworks module, patch or
delivery-code change is a new compatibility profile that needs the ladder and
hardware receipts again. Patches are delivered as a generated exact-hash
overlay plus a shim for spawned EngineCore and worker interpreters, activated
before any Ray or vLLM import, and proven by a receipt from every planned
process. Prefer a dependency's own environment controls: monkey-patching a Ray
Serve constant had no effect because the module had already imported it by
name, and user site hooks never reach vLLM's spawned EngineCore. Never patch
installed site packages in place.

## 5. Gateways, clients and serving settings

**HAProxy is the reference gateway.** Health checks target each node proxy's
`/-/healthz`, never a model route: per-replica checks on a model route at 256
nodes produced about 500 layer-7 timeouts, 800 DOWN events and 20-37% client
errors, while `/-/healthz` produced none. Native configuration validation
(`haproxy -c`) runs before launch, the root owns the gateway process, and its
death ends READY. `http_no_delay` (default on) passed both on and off at one
node; that was a confound check, not a throughput claim.

**Gateway capacity by scale.** Measured with an 8B model, 64-token prompts and
outputs, offered 110 requests/s per node (just above the single-node knee of
about 109), so attainment figures are a saturation stress:

| Gateway | Measured behaviour |
|---|---|
| HAProxy, non-streaming | 107 requests/s at one node; 6,845 at 64 nodes; 27.1 thousand at 256 nodes with 0.04% errors (four client nodes, a large `maxconn` and automatic threads) |
| HAProxy, streaming | 102 requests/s at one node; 384, 1,517 and 5,850 at 4, 16 and 64 nodes with no errors; plateaus at about 4.7 thousand from 128 nodes (see below) |
| Direct dispatch, one client per node (validation only) | 372-392, 1,475-1,495 and 5,323-5,584 requests/s at 4, 16 and 64 nodes; 18.1-19.4 thousand streaming at 256 nodes with no errors |
| Envoy (validation only) | clean through 16 nodes; 64-node non-streaming 6.8 thousand with no errors; 64-node streaming at its limit (one clean pass at 4.9 thousand, three passes with 20-37% HTTP 503 connect timeouts) |
| Ray Serve head-only proxy (validation only) | clean at one node; at 4 nodes non-streaming p50 13.9 s; at 16 nodes 55% and 31% success, at 64 nodes 31% and 15% (non-streaming and streaming) |
| LiteLLM, eight workers (validation only) | 107 requests/s non-streaming at one node; 92% success non-streaming and 49% streaming at 16 nodes; 90% and 40% at 64 nodes (from a later preview on a different snapshot with relaxed start-up and request budgets; in the paper's run LiteLLM's streaming success fell to 7.7% by 64 nodes) |

Even without collapse, HAProxy adds time to first token at 64 nodes: at a
below-knee rate, direct dispatch cut median TTFT from 1.22 s to 0.64 s.

**Do not route streaming for more than about 64 nodes through one head-node
proxy.** At 256 nodes streaming through one HAProxy completed 99.6-100% of
requests but with p50 5.2-5.9 s, p99 17-33 s and drains of up to about six
minutes, while server-side TTFT and TBT stayed at 54/66 ms and 24/28 ms. The
head node held about 200 thousand established connections and TCP
retransmissions grew in lockstep with them: per-token SSE packets over that
many long-lived connections on one node cause a retransmission collapse.
Measurements ruled out CPU (about 98% of the head idle), accept queues,
TIME_WAIT, host NIC drops and descriptor, thread and memory limits. Turning
off `http_no_delay` (coalescing) halved retransmissions and doubled the warm-up
rate but did not fix it. Plan per-node or hierarchical ingress for large
streaming deployments; untested candidates are L4 balancing, HTTP/2, several
tokens per SSE event and proxy-node network tuning. When client-side streaming
numbers collapse at scale, check server-side TTFT and TBT before blaming the
model servers.

**HAProxy threads.** A single HAProxy thread pegs one core and cost 23% of
streaming throughput at 64 nodes; below about four threads HAProxy is
CPU-bound, above that it is network-bound (forcing 32 threads at 256 nodes
changed nothing). ExaServe leaves the thread count to HAProxy unless
`gateway.worker_count` is above 1 or `gateway.options.nbthread` is set
([B5](KNOWN_ISSUES.md#b5-haproxy-thread-count-follows-gatewayworker_count--resolved)).

**Size `maxconn` for the expected concurrency.** ExaServe requires
2 x `maxconn` + backend count + 256 descriptors under the hard `RLIMIT_NOFILE`
and refuses to launch otherwise. Compute nodes allowed 1,048,575 descriptors,
soft and hard, both in the batch job and under `mpiexec` (measured in October
2026); the 16,384 limit of login nodes does not apply to the gateway.
Historical 256-node streaming runs held up to about 162 thousand HAProxy
descriptors. The default `maxconn` of 8,000 is conservative (it fits a 16,384
limit with 64 backends); size `maxconn` to offered rate times end-to-end
latency plus headroom, and check the hard limit the job actually sees on a new
system.

**Rare HAProxy death.** About one in twelve 256-node streaming ramp-ups lost
the HAProxy process after a healthy warm-up (threads dropped to zero, no OOM or
segfault message); the next pass got 100% ECONNREFUSED. It is not resource
exhaustion or a leak; the cause is unknown
([B2](KNOWN_ISSUES.md#b2-centralized-256-node-streaming-congestion-and-rare-haproxy-death)).
The supervisor now records the gateway's exit code and signal as the first
cause. Separate this total failure from the common congestion regime above.

**Envoy and other pooling gateways.** Ray Serve's HTTP server closes idle
connections after 90 s, so a gateway that pools upstream connections must
retire idle ones sooner; Envoy closes them after 60 s
(`proxy.options.upstream_idle_timeout_s`), which removed HTTP 503
"upstream connect error" bursts at the start of later passes.

**LiteLLM.** Keep the Ray parent and model actors in the site environment and
launch only the gateway from the LiteLLM interpreter
(`EXASERVE_LITELLM_PYTHON_PATH` or `backend.args.ray.proxy.python_path`):
activating the LiteLLM virtual environment for the whole job put a NumPy
version ahead of the one vLLM needs, and model actors failed before READY.
LiteLLM initializes every worker before binding (51-59 s), so the compiler
gives it at least 120 s to start. An apparent LiteLLM scaling loss at 16 and
32 nodes was client starvation, but even with enough client concurrency one
LiteLLM gateway saturates from about 4 nodes (streaming) and 16 nodes
(non-streaming): use it for small-scale validation only. On one node it added
about 0 ms of latency at low load and about 40 ms at the median under
overload; its latency overhead at larger scale has not been measured. It
buffers streamed responses, so its runs contribute throughput, errors and
end-to-end latency only, never time to first token or time between tokens.

**Overload experiments.** Under deliberate overload READY is revoked while
canaries time out and re-granted after the drain. A saturated 64-node pass took
489-642 s to drain, longer than the default `recovery_deadline_s` of 60 s,
which ends a healthy but saturated run with READINESS_RECOVERY_EXPIRED. The
head-only and LiteLLM gateways get raised floors; for HAProxy or Envoy set
`deployment.readiness.recovery_deadline_s` above the expected drain time.

**Measure TBT on the server when the proxy coalesces.** With `http_no_delay`
off, HAProxy flushes the SSE stream about every 220-230 ms, so client-side TBT
measures the flush (a 250 ms TBT objective failed although true decode was
about 30 ms). With coalescing, report TTFT client-side with the offset noted and
TBT server-side; with `http_no_delay` on (the default) client TBT is valid. The
option sits in HAProxy's defaults section and also affects non-streaming
responses. Turn on `collect_stats` for scale runs: each replica pushes a
summary every 10 s to one collector and the run gets one
`replica_stats_all.json`; require coverage of every replica and treat a
missing statistics file as a failure.

**Settings that worked for 405B.** Accepted 405B (TP=8 x PP=2) cells used
`gpu_memory_utilization` 0.95 (at 0.90 one tile had effectively no KV-cache
blocks left), `enforce_eager: true`, `max_num_seqs` 8, `max_model_len` 4096,
`replica_max_ongoing_requests` 16, readiness initial deadline 7,200 s,
recovery 3,600 s, canary 300 s, `control.watchdog_cleanup_deadline_s` 900,
`local_stage_path: /tmp/...`, `clean_stage: true`, HAProxy `leastconn` with
`maxconn` 8000, and a client at 0.2 requests/s per node with at most four
client nodes and a 3,600 s request timeout. Re-derive memory utilization when
the model, tensor-parallel size or framework changes.

**Settings for an 8B model on one node.** With 2,048-token prompts and 128
output tokens, a node served about 22-25 requests/s (about two per replica) and
neither `replica_max_ongoing_requests` (4-256) nor `max_num_seqs` (8-128)
mattered: long prompts saturate compute. With 64-token prompts and outputs a
node served 109-118 requests/s, and `replica_max_ongoing_requests: 256` beat 64
(118 against 109 requests/s; p50 at 100 requests/s 83 ms against 204 ms).
Re-characterize single-node saturation for each workload, raise
`replica_max_ongoing_requests` (default 32) for short high-rate requests, drive
scaling runs at a stated fraction of measured saturation, and discard the first
run as warm-up.

**Size the client by Little's law.** In-flight requests equal rate times
latency. At 16 nodes a client with 1,024 request slots, facing 280 requests/s
at about 5 s latency, reached only 73% of the target and stretched a 60 s trace
to 85 s; with enough slots it matched one client per node. The Go client now
derives its active-request budget from 80% of the ephemeral port range and the
replay engine splits it across processes. Treat a dispatch phase that outlasts
the trace as client backpressure, not server saturation.

**One client host has two ceilings.** Ephemeral ports bound slow servers (one
host drives about 300 nodes of second-latency LLM load) and kernel loopback TCP
bounds fast ones (one Go process dispatches roughly 90-160 thousand requests/s;
twelve processes up to about 625 thousand). Rule of thumb:
`max_nodes = min(0.8 x ports / (rate_per_node x latency), dispatch_ceiling / rate_per_node)`.
Beyond that, distribute clients. At 256 nodes a client on the head node capped
measured throughput at about 13.8 thousand requests/s with or without HAProxy,
while one client per node reached 26.9 thousand; before blaming a gateway at
large scale, check whether one host drives all the traffic.

**Client hygiene.** Start each client test from a clean TIME_WAIT state (the
replay engine waits 75 s between runs) and read `dispatch_health` before
trusting a result. Never let several client processes on one node each size
themselves to the full port budget: a 12-process run with 10,240 in flight each
failed with `pthread_create failed`. State `direct_dispatch` (local, mesh or
paired) whenever per-node client results are compared; early "direct" runs hit
the local node while later ones spread over all backends.

**Client node count in eval runs.** An omitted `client.num_nodes` is derived
for every matrix variant: at most four client nodes for proxy runs, one per
deployment node for direct runs. An explicit or matrix-derived value is kept as
written. Proxy results from specs older than this rule used one client rank
per deployment node unless the matrix targeted or derived the count; check the
client node count in the materialized `run.yaml` before comparing with them
([C5](KNOWN_ISSUES.md#c5-client-topology-footgun--resolved)).

**Newer Ray releases.** Ray Serve 2.55 and later can let HAProxy route straight
to HTTP servers inside ingress replicas, with gRPC between deployments, which
removes the Python proxy from the request path. On the pinned Ray 2.53 the best
available shape is the current one: an external HAProxy over per-node proxies.
Measure the native options against it before adopting them.

## 6. Failures, recovery and shutdown

**Exit codes.** The launcher exits 0 on success; 2 when allocation identity,
plan compilation or persistence, site preparation or compatibility activation
fails before launch; 143 only for an operator-requested shutdown; otherwise 1
or the failing child's code. Eval exits 3 for a partial run. Stop a deployment
through the scheduler (`qdel`): the composition root drains, publishes
DRAINING and then STOPPED, and exits 143. An owned child killed by a signal is
a failure, not a drain.

**Diagnose from the typed first cause.** Start with
`exaserve-status show --run-dir DIR --json` and read the terminal reason code
and detail. The first cause is authoritative; later cleanup errors are
secondary. Reason codes include READINESS_REVOKED, READY_EVIDENCE_CHANGED,
READINESS_RECOVERY_EXPIRED, GATEWAY_FAILURE and FIRST_CAUSE; supervisor causes
include UNEXPECTED_EXIT, INVALID_RESULT, START_FAILED, DEADLINE, CLEANUP_ERROR
and SHUTDOWN_REQUESTED. Scheduler walltime expiry appears as
SHUTDOWN_REQUESTED, not as an application failure.

**Recovery is fail-closed.** Every planned rank must register before START and
one missing rank ends the generation; a disconnect revokes READY at once; a
gateway process exit after READY is terminal; a live gateway that fails health,
route or canary checks moves READY to VALIDATING and returns to READY or fails
at the recovery deadline (60 s by default). There is no degraded mode. Recover
from a lost rank or gateway by starting a new generation.

**Harmless noise.** Ray metrics-exporter "RpcError 14" warnings appear because
the site profile disables metrics collection; exit 143, HAProxy -15, SIGTERM
and actor-killed messages appear during a requested teardown. Real failures
look different: a killed Ray head child shows `exit=137`, a lost worker
supervisor shows "authenticated rank control session disappeared without
GOODBYE". After a head or worker loss the Ray driver keeps retrying for up to
120 s; size cleanup windows above that and do not advertise instant recovery.
Decide pass or fail from the status record, the shutdown report and the
terminal record, never from log keywords or raw exit codes.

**Size the cleanup watchdog for the node count.** At 64 nodes a 120 s cleanup
watchdog expired after 55 of 64 drain acknowledgements although every node
was clean. `control.watchdog_cleanup_deadline_s` now defaults to 300 s (the
405B specs use 900 s); a quarter of the remaining budget is reserved for the
all-rank drain and goodbye exchange and gateway stop gets at most 30 s. Accept
a run only when its shutdown report shows a clean all-rank drain and goodbye
with no exhausted deadline.

**Read the structured diagnostic first.** Ray often reports only "Failed to
update the deployments". ExaServe records each engine worker's constructor
phase, the exception type, a subprocess return code or signal, and bounded
head and tail of stderr; read that before re-running, because a missing
stdout line proves nothing about the failing phase.

**Cleanup is scoped and proven per host.** Cleanup signals only strictly older
generations of the same deployment identity, a node-local guardian owns the
Ray process group, and `clean_stage` is a non-destructive barrier: only the
owner of a failed attempt removes its candidate, never another attempt's
published cache. Prove cleanup with per-host process audits keyed by
deployment and generation; a launcher's exit does not show that remote
processes are gone.

## 7. Measuring correctly

**Weak-scaling efficiency includes the drain.** The replay result's duration
runs from start to the last completion on any rank, so the denominator includes
the slowest node's drain. Per-node direct streaming looked like 71% efficiency
at 256 nodes although nothing was lost; efficiency matched T / (T + drain)
within 0.5% in every cell. Report throughput over the send window and the
drain separately (`eval/scripts/direct_stream_window_analysis.py`), use long
runs, and do not compare one lucky single-node run with a large aggregate
(single-node p50 at saturation varied from 3.3 to 10.2 s between runs).

**Lower latency at the largest scale usually means under-loaded servers.**
When a client or gateway limits throughput, per-replica queues shrink and
latency falls. Compare latency only at matched achieved throughput, and check
achieved against offered rate first.

**The saturation finder.** Each step's window includes the tail of in-flight
requests, so achieved over target never reaches 0.95 against real streaming
servers (about 0.83 with 15 s steps); with the default plateau ratio of 0.95 it
reported 25 requests/s for a workload that saturates at 109-118. For
second-latency servers set `plateau_ratio` well below 0.95 or lengthen the
steps, and confirm the answer with a fixed-rate replay.

**Measurement I/O on the shared filesystem distorts results.** Writing probe
records or trace files to Lustre inside the measured window added 600-1,000 s
to start-up at 128-256 nodes; several early numbers came from such runs and are
superseded. Write node-local, gather once in band, and keep tracing off unless
diagnostics are requested. To diagnose Ray's control plane, enable its built-in
GCS event statistics with `deployment.runtime.instrumentation` (validation mode
only), parse them with `eval/tools/parse_gcs_event_stats.py`, time each phase
separately and compare the slowest component, not the mean, with a wait.

**Only complete, authenticated results count.** A run is accepted only when
every result-manifest entry is authenticated, the expected rank set is
complete, the shutdown report is clean, and the scheduler shows the job
finished (PBS state F) with exit status 0; withhold acceptance while PBS shows
E. Incomplete runs become PARTIAL (exit 3) with reasons: do not plot them. A
crash after local completion is a failed run; never infer counts from local
logs.

**Inputs.** Eval runs the committed snapshot: commit before materializing, or
pass `--allow-dirty` knowing it records and excludes the dirty files. Trace
identity covers arrival mode, input content and tokenizer, so produce new trace
inputs instead of editing them in place, and delete a suspect cache entry
rather than editing it. Truncating a prompt by decoding and re-encoding can
overshoot `max_model_len` (about 6% of one workload's requests did); trace
generation now re-checks the token count.

**Calibrate load against the objective, not only the throughput knee.** The
paper's objective is TTFT at most 2 s and a per-request p99 TBT at most 250 ms
(streaming). The 8B rates below are 90% of single-node saturation. The 120B
rate was chosen against TTFT at most 1 s and the same TBT bound, the objective
the scoring tools used at the time; that is stricter than the paper's, so the
120B rate is conservative. Large models become TBT-bound before throughput
saturates: for a 120B model the knee rate gave p99 TBT 568 ms and attainment
0.14, while 9 requests/s per node met the stricter objective. Calibrate each
model and workload on one node by binary search, run robustness cells at about
90% of saturation, and say whether each cell is meant to sit below or above
the knee.
Rates used, in requests/s per node:

| Workload (8B unless noted) | Rate |
|---|---|
| 64-token prompt, 64-token output | 98 (knee about 109) |
| 2,048 in / 2,048 out | 3.6 |
| 4,096 in / 2,048 out | 1.8 |
| code, 256 in / 512 out | 5.4 |
| chat, 256 / 256 | 10.8 |
| summary, 768 / 256 | 10.8 |
| 120B model | 9 |
| 405B, TP=8 x PP=2 | about 0.25-0.3 per replica |

**Trace pitfalls.** Arrivals from `azure_trace` follow the trace window and are
not scaled by node count (one replay delivered the same 19 requests/s at 1 and
64 nodes); scale fixed-rate traces explicitly or keep them out of scaling
claims. Dataset rows longer than the context fail on every pass (three ShareGPT
records were 5-20 thousand tokens against a 4,096-token limit); check lengths
against `max_model_len` before a sweep. A canary whose rate times duration
rounds to zero requests stops at materialization.

**Timing validity.** Results that reuse a verified node-local model cache have
comparable throughput and latency but not comparable cold-start, broadcast or
bring-up times; measure cold start in a fresh allocation or with a fresh cache
root and record it. Pausing the eval driver during a timed phase invalidates
that timing. Buffered logs go quiet during the 75 s cooldown between passes;
never stop a run because its logs are quiet.

**Counters that locate a network wall.** Throughput and error rates alone
cannot separate CPU, accept queue, ports, NIC, fabric and process failures.
On a proxy node sample every few seconds: TCP retransmissions, established
connections, `TCPAbortOnData`, listen overflows and drops, TIME_WAIT count,
proxy CPU, threads and descriptors, system threads, available memory, and
per-interface `rx_dropped` and `rx_fifo_errors` (readable without privilege).
Retransmissions rising in lockstep with connections indicate congestion; zero
host NIC drops place loss in the fabric or TCP. ClientLab's `netstats`
collector uses `benchmarks/netstats.py`; keep any sampler light and out of the
launch path.

**Status-reading traps.** A running scheduler job is not READY; PBS output
files exist but are empty right after start; replay ranks are client ranks
(the 405B spec uses at most four), not deployment nodes; capsule hashes differ
between cells of one campaign because they include run-specific plans, so
compare source snapshot hashes to show "same code"; plotting consumers can pin
run groups, so check which ones they read before publishing a figure. Take run
directories and endpoints from the submission or status record, never by name
order, modification time or log grep.

**MPI result aggregation.** Object receives in mpi4py default to a 32 KiB
buffer; larger chunks failed with "Message truncated", and a 256-node replay
once lost rank 0 after every client had finished. Results now travel as
explicitly sized byte frames (header at most 4 KiB, chunks at most 1 MiB) with
the typed `Ireduce`. Qualify aggregation with multi-rank payloads well above
32 KiB, and never let test doubles define MPI methods the site library lacks.

## 8. Qualification and evidence

**What exists today.** No artifact of the current tree is production-qualified;
production submission fails with `production execution is not qualified`.
Hardening-era hardware campaigns ran with `validation_mode: true`; do not set
it to get past the error. See the [hardening status](hardening/STATUS.md).

**A runtime, storage or control-plane change invalidates earlier evidence.**
Rerun every point of a scaling curve from one snapshot, or label it a
mixed-campaign comparison; keep failed runs as immutable negative evidence and
never resubmit them; build a new candidate instead of relabelling receipts or
updating old artifact hashes. Before reusing a measurement, compare its source
snapshot and site and compatibility hashes with the candidate's.

**Predeclare and gate.** Before requesting nodes, write and hash the experiment
plan: gate, attempt and attempt limit, logical and physical nodes, queue,
walltime, expected runtime and output path. Submit the next cell only after the
previous one passes strict acceptance; stop on the first failure and diagnose
before spending more node-hours; a retry needs a diagnosed change and a fresh
identity. A failure before workload start does not consume the attempt. Stop a
broken attempt early instead of letting it run to the READY deadline.

**Prove the production path.** A finding is fixed only when its invariant holds
on every reachable production consumer, a negative test shows fail-closed
behaviour, and durable evidence is recorded first. A unit-tested helper that
the default path never calls proves nothing: write negative tests against the
real entry point (CLI, YAML loader, matrix expansion), and prove that a
fail-closed check can see a correct state before trusting what it reports.
Count closure from the validated [findings ledger](hardening/FINDINGS.yaml),
never from a status headline, and record scope decisions with a named human
owner, timestamp and evidence.

**Release gates.** Build the wheel from the sdist in an isolated environment,
install the exact wheel into a clean environment, and run the suite outside the
source tree on a compute node, together with typed-core mypy, Ruff, Go checks
and the findings validator. Rerun the gates and rebuild the candidate after any
tracked change, and state what each gate proves in its own terms (modules
checked, validation mode, node tier). Validation tools must obey the runtime's
locality rules; a tool that reads shared storage from workers cannot qualify
an invariant it breaks.

**Canaries before campaigns.** Expensive runs failed on defects that a
one- or two-node canary exposes (pipeline-parallel actor start, cache seeding,
socket paths, MPI aggregation) and on instrumentation itself. Run the matching
canary under `eval/specs/arxiv-submission/smokes/` after any stack change and before
any run of 64 nodes or more, for example `pp_compatibility_canary_2node`
(PP start-up without model bytes), `pp8b_real_engine_canary_2node` (the real PP
engine path with about 21 GB instead of 816 GB),
`nullcompute_haproxy_mpi_large_raw_2node` (replay aggregation above 32 KiB),
`nullcompute_haproxy_subset_cancel_2node` (allocation subsets and cancellation)
and `clean_stage_check_1node`. Design one control cell that decides whether a
broad re-run is needed.

**Campaign acceptance and sizing.** Fix the acceptance rules before a campaign
starts and apply them to failures as strictly as to successes: complete success
means a SUCCEEDED state, a complete manifest, every scheduled request completed
with zero errors and immutable source, plan, site and allocation identities.
Deliberate overload cells count only as measured-partial results with every
request and rank accounted for; never relabel them. Retry a node hardware fault
on clean nodes under a new identity, and pin the exact result per node count in
figure inputs. Size from a cost model: bring-up about 4 minutes for 8B, 7 for
120B, 35 for null compute at 256 nodes with the paper-era
one-application-per-node layout (about 9-10 minutes with the later
node-grouped layout) and about 60 for 405B, plus about 2.25 minutes per pass
(60 s trace and 75 s cooldown). Pilot every cell at two passes (warm-up and one
measured) before the full sweep, plan re-runs at 256 nodes (node failures are
more likely), and materialize 128- and 256-node traces on a compute node
(planner workers grew to about 2.7 GiB each). Spec names must be unique across
`eval/specs` because lookup uses the file name.

**The allocation must match the deployment.** Runs that attached a 32- or
64-node deployment to a 256-node Ray cluster had to be excluded. The compiler
requires `scheduler.nodes` to equal `deployment.num_nodes` unless a reservation
topology is declared, and an oversized nodefile is rejected rather than
truncated. Check the active Ray node count against the planned count in every
result.

**Tests.** Keep tests hermetic: inject doubles through configuration or
environment that child and forkserver processes inherit, never through
parent-process monkeypatching, and never call an undeclared host executable.

## 9. Engineering rules for contributors

- Put every cross-field rule in the plan dataclass or its loader, not only in
  the compiler, and add a direct-construction test and a rehashed-load negative
  test. Never edit a persisted plan; compile a new one.
- Configuration is strict: unknown and duplicate keys, quoted booleans,
  non-finite numbers and model-identifier collisions are rejected. Fix the
  configuration, not the validator.
- Write authoritative state with the `state.atomic` helpers, pass the
  `expected_revision` you read to every status write (the store refuses a write
  without it), and wrap anything that can outlive a lease in a lease heartbeat. On a new shared filesystem, re-verify
  `O_EXCL` and rename atomicity first.
- Use argument vectors, not shell strings. In generated scripts, never place
  `shlex.quote` output inside double quotes (a `$(...)` value once executed
  that way); test every renderer with `$()` and backtick payloads.
- No shell script or second supervisor may own lifecycle; new long-lived
  children are registered with the runtime supervisor in their own process
  group. Remove migration switches and duplicate paths at cutover.
- Pass every identity that two processes must agree on explicitly and override,
  rather than default, inherited values; never match Serve evidence by model id
  (Serve names applications differently).
- Telemetry actors are deployment-scoped, owned by the run and never detached.
  `/metrics`, `/health` and `/stats` are per-replica handlers behind the
  balanced route; use `exaserve-status` for deployment health and correlate
  requests through `X-Request-ID`.
- If one of these symptoms returns, treat it as a regression in the named
  mechanism rather than a site problem: a pre-START heartbeat timeout at 64
  nodes (heartbeats anchored to the last acknowledged message); teardown
  acknowledgements missing from fast ranks (frozen delivery set); `__pycache__`
  written into an immutable snapshot (`PYTHONDONTWRITEBYTECODE=1`); paths with
  `..` escaping the staging root; 16- and 128-node deployment identities
  colliding (bounded hashes, never truncation); `__LMOD_` variables carrying
  login-home entries into children; model directories with Hugging Face cache
  symlinks failing to stage.
- Settings from historical run recipes do not carry over: the degraded-start,
  legacy-lifecycle and readiness-marker switches are gone and there is no
  escape hatch.

## 10. Open problems

- Proxy start-up cost at scale of the current layouts (one application plus
  proxy anchors for dense HAProxy plans; one application per replica for most
  others, see section 4), and whether `RAY_SERVE_RUN_ROUTER_IN_SEPARATE_LOOP=1`
  removes proxy stalls.
- Whether the raised GCS budgets let one Ray cluster pass 512 nodes; whether
  more GCS server threads raise read throughput.
- Real-runtime proof of the shared-filesystem rule: a non-head syscall trace of
  a real staged-model Ray/vLLM run, and per-rank shared-open counts at scale.
  Only the native bootstrap has a syscall-level proof (two nodes).
- Measured site control and readiness limits, and a recorded decision on the
  release ceiling.
- Output-correctness canaries for pipeline-parallel topologies and models
  beyond the real PP=2 canary, which showed no layer fallback when rerun under
  the new policy
  ([D5](KNOWN_ISSUES.md#d5-pipeline-parallel-patches-fall-back-to-a-representative-layer--fails-closed-in-production)).
- The slower data rate of pipeline stage 0 in 405B staging.
- 405B non-streaming at 64 and 128 nodes (`pp405b_pp2_haproxy_nostream_v040`):
  the sequential allocation-campaign attempt failed during model staging
  (storage), and those points are missing; the retained records do not
  diagnose the failure.
- Streaming through one head-node HAProxy beyond 64 nodes (see section 5);
  distributed or hierarchical ingress is the design direction, untested.
- The rare HAProxy process death at 256 nodes, and Envoy's 64-node streaming
  errors, are not explained.
- Strong scaling (fixed workload, more nodes), tail latency (p99 and p999), the
  null-compute routing matrix beyond 256 nodes, and current-code reruns of the
  4-64-node gateway cells.
- Untested at scale: node loss under load (a generation does not survive it;
  resubmit as a new generation), a long idle period followed by a burst,
  autoscaling latency, variable-length workloads and HTTP/2 clients.
- Model staging is serial across models, and there is no request caching at
  the proxy.
- Copper (ALCF's cooperative read-only cache) for Python fan-out is a design
  option if staging fan-out ever dominates start-up; it has never been measured.
