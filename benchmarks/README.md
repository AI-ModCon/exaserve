# Benchmark helpers

This directory is not a deployment or experiment entry point and is outside the
production release surface.

- `netstats.py` samples `/proc/net/dev`; ClientLab's `netstats` collector runs
  it, and [stats.md](stats.md) explains its fields and how to read them.
- `analyze.py`, `plot_internode.py` and `port_model.py` are legacy analysis
  helpers for an older result format; nothing else in the repository uses them.

The pre-hardening benchmark harness (client, proxy and stub launchers and shell
orchestrators) was removed: it generated a retired manifest format and owned
process groups outside the canonical supervisor. Use ClientLab for client,
proxy, synthetic-target, saturation and internode studies:

```bash
python3 -m clientlab plan clientlab/specs/client_microbench.yaml
python3 -m clientlab run clientlab/specs/client_microbench.yaml --local
python3 -m clientlab report <study-directory>
```

Use `python3 -m eval.cli` for serving experiments, and follow `AGENTS.md` for
every nontrivial or multi-node run. Measured client ceilings and network
diagnosis practice are in the
[operations handbook](../docs/operations_handbook.md).
