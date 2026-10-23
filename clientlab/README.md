# ClientLab

ClientLab is a standalone measurement system for studying `eval/go_client/bin/go_dispatch` under controlled conditions.

## Entry Points

- `python3 -m clientlab plan <spec>`
- `python3 -m clientlab run <spec> [--local|--pbs]`
- `python3 -m clientlab report <study_dir>`
- `python3 -m clientlab compare <study_dir_a> <study_dir_b>`
- `python3 -m clientlab smoke <preset>`

Built-in presets live in [`clientlab/specs`](specs):

- `aurora_internode`
- `client_dispatch_ceiling`
- `client_dispatch_scaling`
- `client_microbench`
- `client_safe_zone`
- `fanout_and_affinity`
- `latency_capacity_map`
- `saturation_smoke`

## What It Produces

Each study writes:

- `study_manifest.json`
- `results_index.json`
- `report.md`
- `report.html`
- `plots/*.svg`

Each point writes:

- `run_config.yaml`
- `trace.jsonl`
- `client_metrics.json`
- `phase_trace.jsonl`
- `target_metrics.json`
- `port_metrics.json`
- `netstats.jsonl`
- `stdout.log`
- `stderr.log`
- `profiles/`
- `derived_features.json`
- `diagnosis.json`

## Spec Shape

Specs use a versioned schema with these top-level sections:

- `study`
- `matrix`
- `client`
- `target`
- `faults`
- `collectors`
- `execution`
- `reporting`

`matrix.axes` supports Cartesian sweeps through dotted config paths such as `client.max_active_requests`.

## Synthetic Target

The built-in synthetic target is `clientlab/targets/cpp_server/bin/synthetic_server --config <json>` (C++, built automatically through the bounded Python compiler boundary).

It exposes:

- `/health`
- `/metrics`
- `/v1/models`
- `/v1/chat/completions`
- `/v1/completions`

Supported fault controls include fixed or distributed service time, service concurrency caps, queue caps, queue delay, injected errors, connection close after response, and reset after response.

## Notes

- Run even smoke studies in a compute session (see `AGENTS.md`); `--local` and preset names do not make a run login-node safe.
- Larger or internode studies should follow the repository PBS workflow in `AGENTS.md`.
- The new Go client metrics use full request lifetime through body drain, not header-return timing.
