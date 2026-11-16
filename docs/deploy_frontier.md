# Frontier (OLCF) validation deployment

Status: **validation only.** The `olcf-frontier` `SiteProfile` has no measured
control/readiness limits and no scale envelope, so every Frontier plan must set
`validation_mode: true` and runs with `production_qualified=false`. Nothing on
this page is a support claim; see [hardening status](hardening/STATUS.md).

## What differs from Aurora

| Concern | Aurora | Frontier |
|---|---|---|
| Scheduler / launcher | PBS, PALS `mpiexec` | Slurm, `srun` (finite steps use `--overlap`) |
| Executable transfer | `mpiexec --transfer` | `srun --bcast=/tmp/` |
| Accelerator | 12 PVC tiles, `ZE_AFFINITY_MASK` | 8 MI250X GCDs, `HIP_VISIBLE_DEVICES` (Ray-owned) |
| Compatibility profile | `aurora-frameworks-2025.3.1-xpu` | `olcf-frontier-rocm711` (same upstream Ray 2.53.0 / vLLM v0.15.0 sources, XPU-only patches SC-09..SC-12 dropped) |
| Serving runtime | `/opt/aurora` module image | archive unpacked to `/tmp/exaserve-site/<stack>` on every node by the job environment script |
| Node-local storage | `/tmp` | `/mnt/bb/$USER` (NVMe, needs `--constraint=nvme`) for models, `/tmp` for the runtime |
| Head address | `<node>.hsn.cm.aurora.alcf.anl.gov` | plain hostname (resolves to `hsn0`) |

The Frontier filesystem facts in `exaserve.site._FRONTIER_FILESYSTEM_SEMANTICS`
were recorded from compute nodes: Orion is Lustre, home/project/software trees
are Cray DVS (NFS on login nodes), `/opt/cray` and `/opt/rocm-*` are
node-local overlays.

## 1. Build the runtime archive (once per stack)

Copy and edit the stack configuration outside the checkout:

```bash
cp scripts/frontier/frontier_stack.conf.example /lustre/orion/<proj>/.../frontier_stack.conf
# set EXASERVE_STACK_ROOT, EXASERVE_SOURCE_DIR, EXASERVE_FRONTIER_ACCOUNT
```

Build on one compute node (about an hour; downloads go through the OLCF proxy):

```bash
sbatch -A <account> -p extended -q debug \
  --export=ALL,FRONTIER_STACK_CONFIG=/abs/frontier_stack.conf \
  scripts/frontier/build_stack.sbatch
```

[`build_stack.sh`](../scripts/frontier/build_stack.sh) creates a conda-forge
Python 3.12.12 at `/tmp/exaserve-site/<stack>`, installs ROCm PyTorch 2.10.0,
builds vLLM from the `v0.15.0` tag for `gfx90a` (version `0.15.0+rocm711`),
installs Ray 2.53.0, mpi4py 4.1.1 against Cray MPICH and HAProxy 3.1.6, copies
OLCF's aws-ofi-nccl 1.19.2 RCCL network plugin (the `rccl-net-plugin/1.0`
module's build for ROCm 7.1.1) into `lib/rccl-net-plugin`, checks them on the
GPU, and writes `<stack>.tar.zst` plus its `.sha256` and pip freeze
under `EXASERVE_STACK_ROOT/runtime`. It refuses to overwrite an existing
archive; a changed stack needs a new `EXASERVE_STACK_NAME` and, if any pinned
version changes, a new compatibility profile.

## 2. Prepare models

Models live under `EXASERVE_MODEL_STORAGE_PATH` as `<org>--<name>` directories
and are staged by ExaServe onto `/mnt/bb/$USER`. Only architectures with
reviewed vLLM model-info seeds are accepted (currently `LlamaForCausalLM` and
`GptOssForCausalLM`). Download on a login node; compute jobs run with
`HF_HUB_OFFLINE=1`.

Pipeline-parallel staging sends each node only its stage's weights, so a
`pipeline_parallel_size > 1` model needs a sharded checkpoint with a
`*.safetensors.index.json`; a single `model.safetensors` is rejected.
`tensor_parallel_size` must divide the model's attention heads and may not
exceed the 8 GCDs of a node: a replica spans nodes only through PP stages.

## Model parallelism across nodes

Validated on 2 nodes: one SmolLM2-1.7B replica with
`tensor_parallel_size: 8` and `pipeline_parallel_size: 2` served 256/256
concurrent requests, first over TCP sockets (job 5921405) and then with the
RCCL network plugin (job 5925651). TP traffic stays inside a node (RCCL
P2P/IPC); the PP send/recv between nodes uses aws-ofi-nccl over the Slingshot
`cxi` NICs with GPU Direct RDMA (`NET/Libfabric/<nic>/GDRDMA` in the RCCL log
with `NCCL_DEBUG=INFO`). The Frontier profile sets what that needed:

- `RAY_EXPERIMENTAL_NOSET_HIP_VISIBLE_DEVICES=1`: vLLM's Ray executor picks a
  device by local rank among all node GPUs, so Ray must not mask each actor;
- `NCCL_SOCKET_IFNAME=hsn0`, `GLOO_SOCKET_IFNAME=hsn0` (bootstrap sockets);
- the values OLCF's `rccl-net-plugin/1.0` module sets for the plugin:
  `NCCL_NET_GDR_LEVEL=PHB`, `NCCL_CROSS_NIC=1`, `HSA_FORCE_FINE_GRAIN_PCIE=1`,
  `FI_MR_CACHE_MONITOR=kdreg2` and the `FI_CXI_*` queue and rendezvous
  settings;
- `ROCM_PATH` is passed through to ranks: Ray finds AMD GPUs through it (there
  is no `/opt/rocm` on Frontier) and otherwise falls back to its NVIDIA
  manager and masks `CUDA_VISIBLE_DEVICES`.

`NCCL_DEBUG` / `NCCL_DEBUG_SUBSYS` set in the job environment script also
reach the engine workers.

Measured cross-node RCCL bandwidth, one GCD per node (probe job 5925639):
send/recv about 23.8 GB/s and all-reduce about 22.6 GB/s at 256 MiB-1 GiB with
the plugin, against 2.5 and 1.2 GB/s with `NCCL_NET=Socket`. That is one NIC's
worth; spreading a full node across its four NICs is unmeasured. SmolLM2-1.7B
moves only a few KB per token between stages, so its serving throughput does
not show the difference.

## 3. Submit

Create two small files next to the stack configuration:

- `env.sh` (the job's `EXASERVE_ENV_SCRIPT`):

  ```bash
  export FRONTIER_STACK_CONFIG=/abs/frontier_stack.conf
  source /abs/exaserve/scripts/frontier/env_frontier.sh
  ```

- a submission environment that sets `EXASERVE_SITE_ID=olcf-frontier`,
  `EXASERVE_SCHEDULER=slurm`, `EXASERVE_PROJECT_ACCOUNT`,
  `EXASERVE_MODEL_STORAGE_PATH`, `EXASERVE_ENV_SCRIPT=/abs/env.sh` and
  `EXASERVE_JOB_PYTHON=/tmp/exaserve-site/<stack>/bin/python3`, and puts the
  checkout's `src` on `PYTHONPATH` for `cray-python/3.12.12`.

Then, from a login node:

```bash
exaserve-serve-submit examples/config.frontier.smollm2.yaml \
  --queue extended --qos debug --walltime 00:30:00
```

`--qos` (or `EXASERVE_DEFAULT_QOS`) is new for Slurm. The Frontier job policy
adds `--constraint=nvme` and does not request GPU GRES: whole nodes are
allocated, all GCDs are visible to steps, and a GRES request would make Slurm
inject a ROCr mask that conflicts with Ray's device assignment.

[`env_frontier.sh`](../scripts/frontier/env_frontier.sh) loads the Cray PE and
ROCm modules, `sbcast`s the archive and unpacks it on every node, builds one
wheel of `EXASERVE_SOURCE_DIR` on the head and installs it on every node, then
removes ambient variables that name shared storage. It does not own readiness,
lifecycle or cleanup.

## Known gaps before any qualification

- Larger PP degrees, multi-replica PP and a network-bound model are untested;
  multi-NIC RCCL bandwidth is unmeasured.
- The stack build pins the main packages but not every dependency: two builds
  two days apart resolved different patch versions of a few small packages.
- The runtime site root is a writable tmpfs: its immutability is an operator
  contract, recorded as `readonly=false` in the profile.
- Every item in [deploy_slurm_amd.md](deploy_slurm_amd.md) still applies.
