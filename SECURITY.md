# Security policy

## Reporting a vulnerability

Do not disclose suspected vulnerabilities, exploit instructions, credentials, or
private operational details in public GitHub issues or pull requests.

Send vulnerability reports privately to the current maintainer, Wenyi Wang, at
[wenyiw@uchicago.edu](mailto:wenyiw@uchicago.edu). Do not use a public issue as a
substitute for a private vulnerability report.

In a private report, include:

- A description of the issue and its potential impact.
- The exact source commit or package version and artifact hash, if known.
- The affected configuration, site/profile, scheduler, vendor runtime, engine,
  gateway, and relevant dependency versions.
- Minimal reproduction steps and sanitized evidence; share only what is needed.
- Any known mitigation or proposed fix.

Do not send live credentials, access tokens, private keys, personal information,
restricted datasets, or sensitive prompts. If credentials may be compromised,
follow your organization's credential-revocation and incident-response process.
Reports affecting a shared HPC system should also follow the site's security
reporting procedure; this project cannot replace the site's incident response.

## Versions and qualification

ExaServe is under active production hardening. There is no published long-term
security-support or backport matrix. Report suspected vulnerabilities against
any identifiable revision; maintainers must determine affected revisions and
the appropriate remediation scope. Do not infer support from a version number,
the existence of a development branch, or a passing CI check.

The [README](README.md) and [hardening status](docs/hardening/STATUS.md) describe
the intended runtime boundary, exact candidates, superseded evidence, and open
qualification gates. Qualification is specific to the artifact and deployment
dimensions; it is not a guarantee that a deployment is free of vulnerabilities.
The current production-candidate design assumes a trusted allocation-internal
network and is not a public Internet service security boundary.

## Deployment trust assumptions

ExaServe's inference endpoints have no authentication, TLS or rate limiting.
HAProxy and the per-node Ray Serve proxies listen on all interfaces of the
allocated nodes, and Ray's own ports are unauthenticated in this
configuration. Anyone who can connect to those nodes can send inference
requests, and anyone who can reach the Ray ports can run code as the job user.
Deploy ExaServe only where the site network limits these ports to users you
trust; ExaServe does not check this.

Model weights, `config.json`, tokenizer and chat-template files are trusted
input and are treated like code. ExaServe loads them with
`trust_remote_code=False`, Hugging Face offline mode and an architecture
allowlist (`LlamaForCausalLM`, `GptOssForCausalLM`) that also pins each
architecture's `model_type`, but these checks are not a sandbox. Stage only models from sources you trust, and keep
`model_storage_path` writable only by the operator. Requests cannot supply
their own chat template.

Ray, vLLM, PyTorch and Transformers come from the qualified Aurora
`frameworks/2025.3.1` module (see
[`requirements/aurora-frameworks-2025.3.1.lock`](requirements/aurora-frameworks-2025.3.1.lock))
and change only through requalification. Advisories against those versions are
assessed against the request surface in
[docs/api.md](docs/api.md#inference-http-surface). Low-severity engine defects
that ordinary requests can reach are accepted until the next requalified stack.

## Coordination and updates

Maintainers should coordinate investigation, fixes, and disclosure privately,
then publish appropriate remediation guidance and security advisories after
assessing exposure and affected users. No response-time or fix-time service
level is currently promised. Avoid public disclosure of actionable details
while a private report is being assessed; agree on disclosure timing with the
maintainers and affected operators.
