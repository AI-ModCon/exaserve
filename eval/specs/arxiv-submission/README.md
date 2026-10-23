# Performance characterization suite

Experiment specifications for ExaServe's gateway comparison, workload
robustness, control-plane and pipeline-parallel characterization on Aurora.
These are the experiments reported in
[ExaServe: Large-Scale LLM Serving on Exascale HPC Systems](https://arxiv.org/abs/2609.10812)
(arXiv:2609.10812), after which the folder is named. Each experiment has
exactly one spec. Measured results, limits and lessons from
these experiments are in the
[operations handbook](../../../docs/operations_handbook.md).

## Layout

| Folder | What | `num_runs` |
|---|---|---|
| `calibration/` | Single-node (or single-replica) saturation finders. Run once per (model, workload); their 90% rates go into the OAT specs. | n/a (binary search) |
| `validation/` | **Pilot sweep**: the complete experiment set, but each cell runs only `2` (run 0 is warm-up, run 1 the data point). Use it to shake out every cell end to end and to measure real per-cell cost before the full sweep. Spec names carry a `_val` suffix so results land in separate run groups. | 2 |
| `full/` | The full sweep. Specs mirror `validation/` minus the suffix: `6` runs for N≤64 (warm-up plus 5 data runs) and `3` for the 128- and 256-node cells (warm-up plus 2). Both SSE (`stream: true`) and end-to-end (`_nostream`) variants. | 6 / 3 |
| `smokes/` | One- and two-node infrastructure checks and canaries (below); re-run them after stack changes. | 1 |

Spec names must be unique across the whole `eval/specs/` tree (the catalog
resolves by filename stem), hence the `_val` suffix convention.

**Results mirror this layout**: run groups land under
`<experiments_root>/runs/<spec-folder>/<spec-name>/runN/` (for example
`runs/arxiv-submission/full/oat_8b_baseline/run0/`), derived automatically from the
spec's location (`spec_runs_dir` in `eval/lib/run_planner.py`). Specs stored
directly under `eval/specs/` resolve to `runs/<name>/`. `runs/arxiv-submission/`
contains only folders that mirror this spec tree, and a folder there means real
data from that suite stage.

All `validation/` and `full/` specs set `launch.clean_stage: true`. Under the
current immutable-cache contract this is a non-destructive, all-rank
reconciliation barrier: every rank returns a cleanup receipt, but normal
startup never deletes a content-addressed cache or ambiguously owned debris
that another concurrent deployment could still use. Only the exact owner of a
uniquely named failed attempt removes that candidate. Consequently,
`clean_stage` alone is no longer a claim of cold model bytes. A cold-start
experiment must use a fresh allocation/local cache root and record that fact in
its run evidence. Source/runtime artifacts use their own content-addressed,
generation-scoped lifecycle. `calibration/` and most `smokes/` leave the
barrier off for iteration speed.

## Suite contents

- **Set 1, gateway comparison:** `proxycmp_{haproxy,envoy,litellm,rayserve,direct}`,
  N ∈ {1,4,16,64}, extended to {128,256} via `proxycmp_<proxy>_scale`. Each also
  has a `_nostream` end-to-end variant at N≤64.
- **Set 2, workload robustness (OAT):**
  `oat_8b_{baseline,poisson,2kx2k,4kx4k,code,chat,summary,burstgpt}` and
  `oat_120b` (rate 9 from `calibration/sat_120b_paper_recal`; the
  throughput-knee rate failed the latency objective), N ∈ {1,64}.
- **Set 3, control-plane null compute:** `nullcompute_scaling` (validation is
  the single `n256_r12` cell; full is the (N, R) matrix to 1,024 nodes, which
  has not been run).
- **Multi-node PP:** demonstration `smokes/pp405b_verify_2node`; an OAT-style
  rate via `calibration/sat_405b_pp2`.

`validation/` also holds the reproducers of the 256-node HAProxy investigation
(diagnostic, `nbthread`, no-delay and client-count cells). They now carry
`maxconn` 8000 and one HAProxy thread, unlike the original measurements; see
the handbook's gateway section before re-running them.

## Metrics

Results use data runs only (warm-up dropped). SLO attainment uses TTFT ≤ 1 s
and per-request P99 TBT ≤ 250 ms and is only meaningful for streaming. The
calibrated rates per workload are listed in the handbook.

## Smokes and canaries

| Spec | Nodes | What it checks |
|---|---|---|
| `smoke_slo_stream_1node` | 1 | HAProxy streaming, TBT and goodput |
| `smoke_slo_stream_rayserve_1node` | 1 | Ray-native proxy TBT buffering |
| `smoke_slo_stream_direct_1node` | 1 | `dest=direct` result gathering |
| `dataset_replay_smoke_humaneval` | 1 | dataset replay with Poisson arrivals |
| `nullcompute_smoke_1node` | 1 | null compute and instrumentation |
| `clean_stage_check_1node` | 1 | non-destructive all-rank cleanup receipt, then READY |
| `serverstats_ttft_{on,off}delay_1node`, `serverstats_ttft_ondelay_2node` | 1, 2 | HAProxy `http-no-delay` effect on TBT and the server-statistics collector |
| `nullcompute_grouped_haproxy_2node` | 2 | dense null-compute layout: node-pinned applications, proxy anchors, exact receipts |
| `nullcompute_haproxy_mpi_summary_2node`, `nullcompute_haproxy_mpi_large_raw_2node` | 2 | replay result aggregation over MPI, including messages above 32 KiB |
| `nullcompute_haproxy_subset_cancel_2node` | 2 | allocation subsets and cancellation |
| `pp_compatibility_canary_2node` | 2 | TP=8 x PP=2 start-up without model bytes |
| `pp8b_real_engine_canary_2node` | 2 | the real pipeline-parallel engine path with a small model |
| `pp2_verify_2node`, `pp2_serve_2node` | 2 | PP=2 replicas serving across two stage nodes |
| `pp2_shard_4node` | 4 | shard-aware PP staging: each stage node receives only its shards |
| `pp405b_verify_2node` | 2 | multi-node PP demonstration with the 405B model |
| `pp405b_pp2_proxyfix_4node` | 4 | HAProxy health checks against `/-/healthz` with PP replicas |

## Cost model

Per-cell model from measured runs: bring-up about 4 min (8B), 7 min (120B), 35
min (null compute at 256 nodes) and about 60 min (405B PP=2, cold); each run
about 2.25 min (60 s trace plus 75 s cooldown). A validation cell takes about
bring-up plus 4.5 min, a full cell bring-up plus 13.5 min. Each cell is its own
scheduler job (no cluster reuse). Queue and walltime per node count come from
each spec's derived scheduler fields (see
[scheduler abstraction](../../../docs/design/scheduler_abstraction.md)); check
current site limits before submitting.

## How to run

In a compute allocation:

```bash
python -m eval.cli run materialize <spec> && python -m eval.cli run submit-all <spec>
python -m eval.plot.goodput -e <spec> --preset paper   # score
```

Order: `calibration/` first, then the `validation/` pilot, then `full/`.

Figures: `eval/plot/arxiv_submission_full_figures.py` writes to `eval/plot/output/arxiv_submission_full/`
(gateway scaling from 1 to 256 nodes, SSE against end-to-end, workload sweep,
64-node latency).
