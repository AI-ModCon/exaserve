# Research findings

These reports retain historical measurements, hypotheses and analysis. They do
not qualify the current runtime or replace the production-hardening plan.
Use the [hardening status](../hardening/STATUS.md) for current candidate evidence
and the [path migration guide](../path_migrations.md) for original path references.

The executable fixed-window analysis now lives in
[eval/scripts/direct_stream_window_analysis.py](../../eval/scripts/direct_stream_window_analysis.py).

## Reports

- [Anyscale Ray Serve Production Architecture: Findings](anyscale_rayserve_production_architecture.md)
- [Bottleneck Profiling: Why Weak-Scaling Degrades at 16+ Nodes](bottleneck_profiling.md)
- [Client Dispatch Ceiling Analysis](client_dispatch_ceiling.md)
- [ClientLab Report: client-safe-zone](client_safe_zone.md)
- [Corrected Scaling Measurements (Overhead-Free)](corrected_scaling_measurements.md)
- [Direct-streaming "shortfall" = fixed-window accounting (RESOLVED 2026-07-27)](direct_stream_window_artifact.md)
- [GCS Contention at Scale — Quantitative Measurement (32/64/128/256 nodes)](gcs_contention_quantitative.md)
- [Instrumentation Walkthrough — What's Patched, How It Fires, What It Measures](instrumentation_walkthrough.md)
- [Next Experiments — Ray Serve Limitation Study](next_experiments.md)
- [Ray Overlay Distribution Design (perf-inst-dev)](overlay_distribution_design.md)
- [Phase 0: Single-Node Server Characterization](phase0_server_characterization.md)
- [ProxyActor Death Cascade at 256n — Stage 3 Bottleneck Investigation](proxyactor_death_cascade_256n.md)
- [Ray Launch Stage Walkthrough](ray_launch_stages.md)
- [Saturation Finder Validation](saturation_finder_validation.md)
- [Centralized Client Scaling Limits](scaling_limits_formula.md)
- [Section 6.1 Probe — Controller Reconcile Tick Breakdown](section6_1_controller_ticks.md)
- [Section 6.2 — Inside `DeploymentStateManager.update()`](section6_2_dsm_breakdown.md)
- [Section 6 Probes — Per-Proxy Breakdown (Definitive Evidence)](section6_probes_evidence.md)
- [wait_proxies Scaling Cliff: Root Cause Analysis](wait_proxies_root_cause.md)
- [wait_proxies Root Cause — Instrumented Analysis (2026-04-15, updated 2026-04-16)](wait_proxies_root_cause_instrumented.md)
- [Weak-Scaling: Llama-3-8B on Aurora](weakscaling_llama8b_v2.md)
- [Weak-Scaling Short v2 (64in/64out, Llama-3-8B)](weakscaling_short_v2.md)
- [Weak-scaling Short v3 — Progress Log](weakscaling_short_v3_progress.md)
