# Performance characterization suite

Experiment specifications for ExaServe's gateway comparison, workload
robustness, control-plane and pipeline-parallel characterization on Aurora.
These are the experiments reported in
[ExaServe: Large-Scale LLM Serving on Exascale HPC Systems](https://arxiv.org/abs/2609.10812)
(arXiv:2609.10812), after which the folder is named; the SGLang engine
experiments are specified outside it ([below](#suite-contents)). Measured
results, limits and lessons from these experiments are in the
[operations handbook](../../../docs/operations_handbook.md).

## Layout

| Folder | What | `num_runs` |
|---|---|---|
| `calibration/` | Single-node (or single-replica) saturation finders, run once per (model, workload); their 90% rates go into the OAT specs. Also the fixed-rate 120B re-calibration (`sat_120b_paper_recal`) and the 405B duration tests at 16 and 192 nodes (`pp405b_pp2_n16_durtest`, `pp405b_pp2_n192_durtest`). | n/a for the finders (binary search); 2 for the others |
| `validation/` | **Pilot sweep**: two-run pilots of the gateway and OAT experiments (run 0 is warm-up, run 1 the data point), 256-node pilots and HAProxy reproducers (below), a direct-dispatch twin of the OAT baseline, the null-compute `n256_r12` cell and the bring-up instrumentation of the paper's Table II. Use it to shake out cells end to end and to measure real per-cell cost before the full sweep. Spec names carry a `_val` suffix so results land in separate run groups. | 2; 1 for the start-up-only `nullcompute_scaling_val` and `bringup_inst_real_val`; 6 for `proxycmp_haproxy_256_diag_val` |
| `full/` | The full sweep. Where a pilot exists, the full spec has its name without the suffix. `full/` also holds specs without a pilot: the 128- and 256-node gateway cells (`_scale`), most `_nostream` variants, the 405B PP sweeps, `direct_topology`, `nullcompute_haproxy_scale_to256_v040` and `proxycmp_envoy_256retry`. | 6 (warm-up plus 5 data runs); 3 (warm-up plus 2) for the streaming `proxycmp_<proxy>_scale` specs; 2 for `pp405b_pp2_haproxy_nostream_v040`, `direct_topology` (per arm) and `proxycmp_envoy_256retry`; 1 for the start-up-only null-compute specs |
| `smokes/` | Infrastructure checks and canaries on one to four nodes (below), except `pp405b_pp2_proxyfix_4node`, which sweeps 4-256 nodes. Re-run them after stack changes. | 1 or 2 |

Spec names must be unique across the whole `eval/specs/` tree (the catalog
resolves by filename stem), hence the `_val` suffix convention.

**Results mirror this layout**: run groups land under
`<experiments_root>/runs/<spec-folder>/<spec-name>/runN/` (for example
`runs/arxiv-submission/full/oat_8b_baseline/run0/`), derived automatically from the
spec's location (`spec_runs_dir` in `eval/lib/run_planner.py`). Specs stored
directly under `eval/specs/` resolve to `runs/<name>/`. `runs/arxiv-submission/`
contains only folders that mirror this spec tree, and a folder there means real
data from that suite stage. A run group's `run.yaml` binds the absolute path it
was written to; to read groups recorded under another folder, set
`EXASERVE_PAPER_SUITE_ROOT` to that folder instead of moving them.

All `validation/` and `full/` specs set `launch.clean_stage: true`, except the
four `full/pp405b_pp2_scale*.yaml` specs, which leave it off. Under the
current immutable-cache contract this is a non-destructive, all-rank
reconciliation barrier: every rank returns a cleanup receipt, but normal
startup never deletes a content-addressed cache or ambiguously owned debris
that another concurrent deployment could still use. Only the exact owner of a
uniquely named failed attempt removes that candidate. Consequently,
`clean_stage` alone is no longer a claim of cold model bytes. A cold-start
experiment must use a fresh allocation/local cache root and record that fact in
its run evidence. Source/runtime artifacts use their own content-addressed,
generation-scoped lifecycle. `calibration/` and half of `smokes/` leave the
barrier off for iteration speed.

## Suite contents

- **Set 1, gateway comparison:** `proxycmp_{haproxy,envoy,litellm,rayserve,direct}`,
  N ∈ {1,4,16,64}, extended to {128,256} via `proxycmp_<proxy>_scale`. Each also
  has a `_nostream` end-to-end variant at both scales (`proxycmp_<proxy>_nostream`
  and `proxycmp_<proxy>_nostream_scale`); the paper's non-streaming HAProxy
  result at 256 nodes is the 256-node cell of `proxycmp_haproxy_nostream_scale`.
  The streaming `_scale` specs run each cell 3 times, not the six times the
  paper describes. `proxycmp_envoy_256retry` is a two-run retry of Envoy's
  streaming 256-node cell, and `validation/` holds 256-node HAProxy and
  direct-dispatch pilots.
- **Set 2, workload robustness (OAT):**
  `oat_8b_{baseline,poisson,2kx2k,4kx4k,code,chat,summary,burstgpt}` and
  `oat_120b` (rate 9 from `calibration/sat_120b_paper_recal`; the
  throughput-knee rate failed the latency objective), N ∈ {1,64}, each with a
  `_nostream` variant in `full/`. `validation/oat_8b_baseline_direct_val`
  repeats the baseline pilot with direct dispatch.
- **Set 3, control-plane null compute:** `nullcompute_scaling`. Validation is
  the single `n256_r12` cell. The full spec is the (N, R) matrix to 1,024
  nodes, which has not been run and cannot be submitted as checked in: its
  cells request three hours on debug-scaling, which `submit` refuses before
  contacting the scheduler; cells above 256 nodes do not compile unless
  `EXASERVE_SITE_MAX_NODES` is raised; and the R = 24 and 48 cells exceed 12
  GPUs per node and are rejected. `full/nullcompute_haproxy_scale_to256_v040`
  measures null-compute HAProxy bring-up at 32-256 nodes.
- **Bring-up breakdown (Table II):** `validation/bringup_inst_real_val`
  instruments real-engine bring-up at 64, 128 and 256 nodes.
- **Multi-node PP (Llama-3.1-405B, TP=8 x PP=2):** the demonstration
  `smokes/pp405b_verify_2node`; the single-replica rate
  `calibration/sat_405b_pp2`; the weak-scaling sweep of the paper's Fig. 5,
  `full/pp405b_pp2_scale` (HAProxy) and `full/pp405b_pp2_scale_direct` (direct
  dispatch), both streaming and each with a `_nostream` variant; the later
  non-streaming HAProxy curve `full/pp405b_pp2_haproxy_nostream_v040`; and the
  duration tests in `calibration/`. These specs request two hours below 256
  nodes and four from 256, so `submit` refuses their 17-255-node cells, which
  exceed the one-hour debug-scaling limit; run those in a reservation queue by
  changing the spec's derived `scheduler.queue` expression.
  Only the 32-, 64- and 128-node cells of
  `full/pp405b_pp2_haproxy_nostream_v040` also fit the allocation campaign
  (two non-streaming runs, clean staging, after a qualification campaign)
  ([handbook](../../../docs/operations_handbook.md#2-plan-the-allocation)).
- **SGLang engine (Fig. 6):** `eval/specs/sglang_haproxy_full.yaml`,
  `sglang_direct_full.yaml`, `sglang_direct_n256.yaml` and the saturation
  finder `sglang_sat_v1.yaml`. The default Aurora site profile rejects the
  SGLang engine, so these specs need a site profile that admits it
  ([open work](../../../docs/TODO.md#external-platform-qualification)).

`validation/` also holds the reproducers of the 256-node HAProxy investigation
(diagnostic, `nbthread`, no-delay and client-count cells). They now carry
`maxconn` 8000, unlike the original measurements; with `num_workers: 1`
HAProxy picks its own thread count, as it did then (the `nbthread` cells set it
explicitly). See the handbook's gateway section before re-running them.

## Metrics

Results use data runs only (warm-up dropped). SLO attainment uses TTFT ≤ 2 s
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
| `pp405b_pp2_proxyfix_4node` | 4-256 | HAProxy health checks against `/-/healthz` with PP replicas |

## Cost model

Per-cell model from measured runs: bring-up about 4 min (8B), 7 min (120B), 35
min (null compute at 256 nodes on the paper-era snapshot; about 9-10 min on
later snapshots) and about 60 min (405B PP=2, cold); each run about 2.25 min
(60 s trace plus 75 s cooldown). A validation cell takes about bring-up plus 4.5 min, a six-run full cell
bring-up plus 13.5 min. Each cell is its own scheduler job (no cluster reuse).
Queue and walltime per node count come from each spec's derived scheduler
fields (see
[scheduler abstraction](../../../docs/design/scheduler_abstraction.md)); check
current site limits before submitting.

## How to run

Run the commands from the repository root with `PYTHONPATH="$PWD:$PWD/src"`
and the site variables of
[getting started](../../../docs/getting_started.md#configure-evaluation-environment-preparation)
set; the eval tooling imports ExaServe from the checkout's `src/`.

Several specs carry publication placeholders in path fields,
`/lus/flare/projects/YOUR_PROJECT/YOUR_USER/...` (`<PROJECT>/<user>` in
`eval/specs/refcard/`): `deployment.model_storage_path` in the 405B and PP
specs, and `trace.input_prompt_path` or `input_trace_path` in the
`oat_8b_{burstgpt,chat,code,summary}*` and `dataset_replay_smoke_humaneval`
specs. A path in a spec overrides the site configuration, so edit these before
`run materialize`: point `model_storage_path` at the directory that holds the
staged model, or delete the line to use the site configuration's path, and
point the dataset paths at the files that `eval/tools/fetch_paper_datasets.py`
wrote under your `user_data_root`.

In a compute allocation:

```bash
python -m eval.cli run materialize <spec-path>   # prints run.yaml paths under a new runN
python -m eval.cli run submit-all <spec-name> --run-group <runN>   # the runN printed above
python -m eval.plot.goodput -e <spec-name> --run-group-name <runN> --preset paper   # score
```

`run materialize` takes a spec path (or a unique spec name); `run submit-all`
and the scorer take the spec name, the file name without `.yaml`.

Order: `calibration/` first, then the `validation/` pilot, then `full/`.

Figures: `eval/plot/arxiv_submission_full_figures.py` writes to `eval/plot/output/arxiv_submission_full/`
(gateway scaling from 1 to 256 nodes, SSE against end-to-end, workload sweep,
64-node latency). The 405B figures (`fig_pp405b`, `fig_pp_engines`) need the
256-node non-streaming HAProxy point that the script pins, and that cell has
not been run, so a default run stops there; render the other figures one at a
time with `--only fig1`, `--only fig2`, `--only fig4`, `--only fig5` and
`--only fig6`.
