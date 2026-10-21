# ExaServe documentation

ExaServe is an allocation-scoped control plane for Ray Serve-based,
OpenAI-compatible LLM inference. Its Aurora runtime combines immutable plans,
supervised processes, and generation-bound readiness. Portable Python tooling
and hardware-qualified serving are separate support boundaries.

## Start here

- [Getting started](getting_started.md): portable development and Aurora setup.
- [Usage](usage.md): configuration, submission, status, evaluation, and ClientLab.
- [API reference](api.md): public plan and status interfaces and installed commands.
- [FAQ](faq.md): environment, qualification, readiness, and contribution questions.
- [AI-ModCon checklist](modcon_compliance.md): requirement mapping, validation
  limits, and GitHub administrator steps for `AI-ModCon/exaserve`.
- [Research findings](findings/index.md): historical measurements and analysis.
- [Documentation path migration](path_migrations.md): old-to-new path mapping
  and preservation of historical evidence identities.

## Architecture and operational authority

User guides, architecture, hardening records, and research reports share this
directory. Their authority is unchanged: research reports do not
override the execution plan or candidate qualification records.

| Topic | Authoritative document or entry point |
| --- | --- |
| Site-neutral safety and permissions | [Repository operating rules](../AGENTS.md) |
| Aurora allocation, toolchain, and runtime setup | [Aurora setup guide](getting_started.md#aurora-development-and-serving) |
| Architecture, implementation, and acceptance gates | [Production-hardening execution plan](PRODUCTION_HARDENING_EXECUTION_PLAN.md) |
| Candidate identities and qualification caveats | [Hardening status](hardening/STATUS.md) |
| Implemented boundaries and design notes | [Design index](design/README.md) |
| Submit-to-readiness control flow | [Call graph](design/call_graph.md) |
| Dependency and site-stack separation | [Dependency profiles](../requirements/README.md) |
| Evaluation control plane | [Eval design](../eval/DESIGN.md) |
| Client measurement studies | [ClientLab](../clientlab/README.md) |

`AGENTS.md` governs where commands may run. The production-hardening execution
plan is the sole architecture and implementation specification; audits, TODOs,
historical results, and these introductory pages cannot override it. Read
supersession notices in the status documents before reusing qualification
evidence. Historical runs do not qualify a changed artifact.

## Project and community

- [Project overview](../README.md)
- [Contribution guidelines](../CONTRIBUTING.md)
- [Code of conduct](../CODE_OF_CONDUCT.md)
- [Security reporting](../SECURITY.md)
- [Changelog](../CHANGELOG.md)
- [Apache License 2.0](../LICENSE) and [notice](../NOTICE)
- [Source repository](https://github.com/AI-ModCon/exaserve)
- [Issue tracker](https://github.com/AI-ModCon/exaserve/issues)

For a bug report, include the command, package or commit identity, environment,
and relevant redacted errors. Do not include credentials, private model data,
or unredacted deployment artifacts in public issues.
