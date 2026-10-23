"""Generate docs/ExaServe_Reference_Card.docx.

Matches the Academy_Framework_Reference_Card.docx visual language exactly:
same palette (rust 9C4A2E/C2613F, navy 2C3340, warm grays), same
direct-formatting idiom, same code-block/callout/table constructs. Uses the
Academy docx as the container (styles/settings/fonts/footers preserved) and
swaps document.xml. The docx is fully generated — edit THIS script, not the
Word file, or your changes will be lost on the next regeneration.

Usage:  python3 tools/make_refcard_docx.py
Needs:  tmp/ref_card/Academy_Framework_Reference_Card.docx as the template and
        the two source figures listed in docs/exaserve.md.
"""

import os
from pathlib import Path
import re
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tmp/ref_card/Academy_Framework_Reference_Card.docx"
OUT = ROOT / "docs/ExaServe_Reference_Card.docx"

RUST = "9C4A2E"
RUST_BORDER = "C2613F"
NAVY = "2C3340"
GRAYTXT = "5B6472"
CODE_BG = "F4F2EF"
LEARN_BG = "FBF1EC"
NOTE_BG = "FCF3E2"
TBL_BORDER = "D9D4CC"
CODE_EDGE = "E2DCD4"
FULL_W = 10224


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def run(text, sz=None, b=False, color=None, font=None, i=False):
    rpr = ""
    if font:
        rpr += f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}"/>'
    if b:
        rpr += "<w:b/><w:bCs/>"
    if i:
        rpr += "<w:i/><w:iCs/>"
    if color:
        rpr += f'<w:color w:val="{color}"/>'
    if sz:
        rpr += f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>'
    rpr = f"<w:rPr>{rpr}</w:rPr>" if rpr else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{esc(text)}</w:t></w:r>'


def par(runs_xml, before=None, after=None, pbdr=None, line=None, jc=None):
    ppr = ""
    if pbdr:
        sz, space = pbdr
        ppr += (
            f'<w:pBdr><w:bottom w:val="single" w:color="{RUST_BORDER}" '
            f'w:sz="{sz}" w:space="{space}"/></w:pBdr>'
        )
    if before is not None or after is not None:
        b = f' w:before="{before}"' if before is not None else ""
        a = f' w:after="{after}"' if after is not None else ""
        ppr += f"<w:spacing{b}{a}/>"
    if line:
        ppr += f'<w:spacing w:line="{line}" w:lineRule="auto"/>'
    if jc:
        ppr += f'<w:jc w:val="{jc}"/>'
    ppr = f"<w:pPr>{ppr}</w:pPr>" if ppr else ""
    return f"<w:p>{ppr}{runs_xml}</w:p>"


def body_par(text, after=80):
    return par(run(text), after=after)


def bold_lead(text):
    return par(run(text, b=True), after=60)


def heading(num, text):
    return par(
        run(f"{num}  ·  {text}", sz=26, b=True, color=RUST),
        before=260,
        after=120,
        pbdr=(12, 3),
    )


def one_cell_table(cell_xml, left_color, left_sz, edge_color, edge_sz, fill, mar):
    top, lft, bot, rgt = mar
    return (
        f'<w:tbl><w:tblPr><w:tblW w:type="dxa" w:w="{FULL_W}"/>'
        "<w:tblBorders>"
        '<w:top w:val="none" w:color="auto" w:sz="0"/>'
        '<w:left w:val="none" w:color="auto" w:sz="0"/>'
        '<w:bottom w:val="none" w:color="auto" w:sz="0"/>'
        '<w:right w:val="none" w:color="auto" w:sz="0"/>'
        '<w:insideH w:val="none" w:color="auto" w:sz="0"/>'
        '<w:insideV w:val="none" w:color="auto" w:sz="0"/>'
        "</w:tblBorders></w:tblPr>"
        f'<w:tblGrid><w:gridCol w:w="{FULL_W}"/></w:tblGrid>'
        f"<w:tr><w:trPr><w:cantSplit/></w:trPr>"
        f'<w:tc><w:tcPr><w:tcW w:type="dxa" w:w="{FULL_W}"/>'
        "<w:tcBorders>"
        f'<w:top w:val="single" w:color="{edge_color}" w:sz="{edge_sz}"/>'
        f'<w:left w:val="single" w:color="{left_color}" w:sz="{left_sz}"/>'
        f'<w:bottom w:val="single" w:color="{edge_color}" w:sz="{edge_sz}"/>'
        f'<w:right w:val="single" w:color="{edge_color}" w:sz="{edge_sz}"/>'
        "</w:tcBorders>"
        f'<w:shd w:fill="{fill}" w:color="auto" w:val="clear"/>'
        f'<w:tcMar><w:top w:type="dxa" w:w="{top}"/><w:left w:type="dxa" w:w="{lft}"/>'
        f'<w:bottom w:type="dxa" w:w="{bot}"/><w:right w:type="dxa" w:w="{rgt}"/></w:tcMar>'
        f"</w:tcPr>{cell_xml}</w:tc></w:tr></w:tbl><w:p/>"
    )


def code_block(text):
    lines = text.rstrip("\n").split("\n")
    runs = []
    for i, ln in enumerate(lines):
        if i:
            runs.append("<w:r><w:br/></w:r>")
        runs.append(run(ln, sz=16, font="Consolas"))
    cell = par("".join(runs), line=248)
    return one_cell_table(cell, RUST_BORDER, 18, CODE_EDGE, 4, CODE_BG, (90, 160, 90, 140))


def callout(lead, text, fill):
    runs = run(lead + "  ", b=True, color=RUST) + run(text)
    cell = f"<w:p>{runs}</w:p>"
    return one_cell_table(cell, RUST_BORDER, 20, RUST_BORDER, 4, fill, (110, 170, 110, 150))


IMG_DIR = ROOT / "docs/figures"
_images = []  # (zip_target, src_path, relationship_id)


def figure(png_name, caption, width_in):
    """Embed docs/figures/<png_name> centered at width_in inches, with an
    italic gray caption underneath (paper-figure style)."""
    import struct

    src = IMG_DIR / png_name
    d = src.read_bytes()
    if len(d) < 24 or d[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"reference-card figure is absent or not PNG: {src}")
    w, h = struct.unpack(">II", d[16:24])  # PNG IHDR
    rid = f"rIdFig{len(_images) + 1}"
    _images.append((f"media/{png_name}", src, rid))
    cx = int(width_in * 914400)  # EMU
    cy = int(cx * h / w)
    n = 100 + len(_images)
    drawing = (
        "<w:r><w:drawing>"
        '<wp:inline distT="0" distB="0" distL="0" distR="0" '
        'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">'
        f'<wp:extent cx="{cx}" cy="{cy}"/>'
        f'<wp:docPr id="{n}" name="{png_name}"/>'
        '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<pic:nvPicPr><pic:cNvPr id="{n}" name="{png_name}"/><pic:cNvPicPr/></pic:nvPicPr>'
        f'<pic:blipFill><a:blip r:embed="{rid}" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/>'
        "<a:stretch><a:fillRect/></a:stretch></pic:blipFill>"
        f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
        "</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>"
    )
    fig_par = par(drawing, before=60, after=40, jc="center")
    cap_par = par(run(caption, sz=16, color=GRAYTXT, i=True), after=120, jc="center")
    return fig_par + cap_par


def data_table(rows, col_w, repeat_header=False):
    def tc(text, w, fill, header):
        rpr = run(text, sz=19, b=header, color="FFFFFF" if header else None)
        return (
            f'<w:tc><w:tcPr><w:tcW w:type="dxa" w:w="{w}"/>'
            "<w:tcBorders>"
            f'<w:top w:val="single" w:color="{TBL_BORDER}" w:sz="2"/>'
            f'<w:left w:val="single" w:color="{TBL_BORDER}" w:sz="2"/>'
            f'<w:bottom w:val="single" w:color="{TBL_BORDER}" w:sz="2"/>'
            f'<w:right w:val="single" w:color="{TBL_BORDER}" w:sz="2"/>'
            "</w:tcBorders>"
            f'<w:shd w:fill="{fill}" w:color="auto" w:val="clear"/>'
            '<w:tcMar><w:top w:type="dxa" w:w="70"/><w:left w:type="dxa" w:w="120"/>'
            '<w:bottom w:type="dxa" w:w="70"/><w:right w:type="dxa" w:w="120"/></w:tcMar>'
            f"</w:tcPr><w:p>{rpr}</w:p></w:tc>"
        )

    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in col_w)
    trs = []
    for ri, row in enumerate(rows):
        header = ri == 0
        fill = NAVY if header else ("FFFFFF" if ri % 2 == 1 else CODE_BG)
        cells = "".join(tc(c, col_w[j], fill, header) for j, c in enumerate(row))
        # no row may split across a page boundary; the header row repeats on
        # the next page only where requested (tables expected to span pages)
        trpr = (
            "<w:trPr><w:tblHeader/><w:cantSplit/></w:trPr>"
            if header and repeat_header
            else "<w:trPr><w:cantSplit/></w:trPr>"
        )
        trs.append(f"<w:tr>{trpr}{cells}</w:tr>")
    borders = "".join(
        f'<w:{side} w:val="single" w:color="{TBL_BORDER}" w:sz="4"/>'
        for side in ("top", "left", "bottom", "right", "insideH", "insideV")
    )
    return (
        f'<w:tbl><w:tblPr><w:tblW w:type="dxa" w:w="{FULL_W}"/>'
        f"<w:tblBorders>{borders}</w:tblBorders></w:tblPr>"
        f"<w:tblGrid>{grid}</w:tblGrid>{''.join(trs)}</w:tbl><w:p/>"
    )


# ------------------------------------------------------------------ content
blocks = []

# title block
blocks.append(par(run("EXASERVE", sz=48, b=True, color=RUST)))
blocks.append(par(run("Framework Reference Card", sz=30, b=True), after=40))
blocks.append(
    par(
        run(
            "Scaling LLM Inference on HPC  —  One OpenAI-Compatible Endpoint "
            "from N Compute Nodes  •  github.com/AI-ModCon/exaserve",
            sz=19,
            color=GRAYTXT,
        ),
        after=140,
        pbdr=(18, 4),
    )
)
blocks.append(
    body_par(
        "ExaServe is a framework for scaling LLM inference across the compute nodes of "
        "an HPC system. From one YAML file and one command, it turns a batch-scheduler "
        "allocation (e.g. a PBS job) into a "
        "single OpenAI-compatible inference service: it launches a Ray cluster over the "
        "allocation, stages model weights to node-local storage with an MPI broadcast, deploys "
        "vLLM replicas in plan-derived Ray Serve applications, and fronts them with one "
        "head-owned HAProxy. A companion evaluation harness measures deployments end to end. "
        "ExaServe has been evaluated from 1 to 256 Aurora nodes, including Llama-3-8B "
        "serving and pipeline-parallel Llama-3.1-405B inference, on earlier snapshots of "
        "this code; the current tree has not been re-measured at that scale. This is "
        "development and research source: no artifact is production-qualified, and "
        "production submission fails closed. Fix-specific regression coverage belongs to "
        "the changelog and does not redefine the system's demonstrated scale.",
        after=100,
    )
)

# 1 Why
blocks.append(heading(1, "Why ExaServe?"))
blocks.append(
    body_par(
        "Existing LLM serving stacks assume cloud environments; HPC systems bring batch-queue "
        "scheduling, MPI-only launch paths, Lustre metadata costs, exotic accelerators, and "
        "scale cliffs that only appear past a hundred nodes. ExaServe packages the "
        "engineering needed to cross that gap:"
    )
)
why = [
    (
        "Turnkey N-node serving",
        "One YAML file plus one command turns a batch-scheduler allocation into an "
        "OpenAI-compatible service; clients see the standard API and need no HPC "
        "knowledge.",
    ),
    (
        "Demonstrated scale",
        "Scale evaluations of earlier snapshots reached 256 nodes / 3,072 replicas "
        "behind an HAProxy "
        "front end: 27.1k non-streaming QPS with Llama-3-8B (one replica per tile) "
        "— 96% of the 28.2k requests/s offered at 256 nodes, with 0.04% errors (0.0% as "
        "rounded in the paper). "
        "A quantified comparison of head-node proxies (HAProxy, Envoy, LiteLLM, Ray Serve "
        "proxy) records gateway-specific throughput and latency limits.",
    ),
    (
        "Frontier-model research",
        "Multi-node pipeline parallelism serves Llama-3.1-405B (TP8 × PP2, two nodes per "
        "replica) with shard-aware weight staging, demonstrated from 2 to 128 replicas "
        "(4 to 256 nodes, streaming): 67% weak-scaling efficiency with direct dispatch "
        "and 50% through HAProxy.",
    ),
    (
        "Measurement built in",
        "A declarative benchmark harness generates traces and scheduler jobs, replays load "
        "through a Go client, and scores per-request TTFT/TBT against latency SLOs.",
    ),
]
for lead, text in why:
    blocks.append(bold_lead(lead))
    blocks.append(body_par(text))

# 2 What's in a deployment
blocks.append(heading(2, "What’s in a deployment?"))
blocks.append(
    body_par(
        "A deployment is a small stack of cooperating pieces, all driven from one "
        "configuration file:"
    )
)
blocks.append(
    data_table(
        [
            ["Component", "Description"],
            [
                "Launcher",
                "exaserve-serve-submit (batch, from a login node) or exaserve-launch-cluster "
                "(interactive) bring up the whole stack on a scheduler allocation",
            ],
            [
                "MPI weight staging",
                "One-source-many-sinks MPI broadcast from the shared file system (e.g., Lustre) to "
                "node-local storage; shard-aware per pipeline stage for very large models",
            ],
            [
                "Inference replicas",
                "Dense HAProxy plans (one model, TP=1/PP=1, a replica on every device) use one "
                "multi-replica model application plus node proxies, and dense null-compute plans "
                "one node-pinned application per node. Other gateways and sparse, multi-device, "
                "pipeline-parallel and multi-model plans keep one application per replica; "
                "replicas span devices as planned",
            ],
            [
                "Head-node proxy",
                "One head-owned HAProxy in the Aurora reference deployment exposes a "
                "single allocation-internal endpoint",
            ],
            [
                "Compatibility profile",
                "Version-pinned targeted activation plus per-process attestation before READY",
            ],
            [
                "Benchmark harness",
                "eval/: declarative specs → traces + scheduler jobs → replay → SLO scoring",
            ],
        ],
        [2800, 7424],
        repeat_header=True,
    )
)

# 3 Installation
blocks.append(heading(3, "Installation"))
blocks.append(
    body_par(
        "Install steps are site-specific — they depend on how the host provides Ray, the "
        "inference engine, MPI, and the accelerator toolchain. The recipe below targets ALCF "
        "Aurora; recipes for other sites will be added as they are supported.",
        after=60,
    )
)
blocks.append(bold_lead("ALCF Aurora"))
blocks.append(
    body_par(
        "Use the operator-provisioned site interpreter and ExaServe wheel together with "
        "the profiled Ray, vLLM, MPI and accelerator stack. On the current Aurora image the "
        "default frameworks module (2026.1.0) fails ExaServe's compatibility check; load "
        "frameworks/2025.3.1 from the 26.26.0 image's module tree with the recipe in "
        "docs/getting_started.md, saved as a site environment script. Job isolation disables "
        "user-site packages, so an installation made only with --user is not a serving "
        "runtime. The README and getting-started guide describe provisioning and preflight.",
        after=60,
    )
)
blocks.append(
    code_block(
        "export EXASERVE_ENV_SCRIPT_AURORA=/lus/flare/projects/YOUR_PROJECT/site-env.sh\n"
        'source "$EXASERVE_ENV_SCRIPT_AURORA"   # frameworks/2025.3.1 recipe\n'
        "PYTHONNOUSERSITE=1 PYTHONSAFEPATH=1 python3 -c \\\n"
        "  'import sys, exaserve; print(sys.executable); print(exaserve.__file__)'\n"
        "command -v mpiexec\n"
        "command -v haproxy"
    )
)
blocks.append(
    body_par(
        "One-time extras: provision HAProxy with scripts/build_haproxy.sh on a compute "
        "node; build the evaluation load generator with make -C eval/go_client after "
        "sourcing the site environment script, which loads go."
    )
)

# 4 Example
blocks.append(heading(4, "Example"))
blocks.append(bold_lead("ALCF Aurora"))
blocks.append(
    body_par(
        "One flat canonical YAML file describes deployment semantics. This compact "
        "example uses two nodes for readability. Before submission, select an authorized "
        "validation configuration or an admitted release profile; the current default "
        "profile fails production admission closed. Submission itself runs from a login "
        "node with the site's project directory (from which the model storage root is "
        "derived) and the job's environment script exported; query the endpoint only after "
        "canonical READY:",
        after=60,
    )
)
blocks.append(
    code_block(
        "export EXASERVE_PROJECT_ROOT=/lus/flare/projects/YOUR_PROJECT\n"
        "export EXASERVE_ENV_SCRIPT_AURORA=$EXASERVE_PROJECT_ROOT/site-env.sh\n"
        "exaserve-serve-submit my_config.yaml --project-account YOUR_PROJECT --wait\n"
        "# 1234567.aurora-pbs-0001...          <- PBS job id\n"
        "# http://<head-node>:4001             <- service URL\n"
        "\n"
        'curl -sS -X POST "http://<head-node>:4001/v1/chat/completions" \\\n'
        "     -H 'Content-Type: application/json' \\\n"
        '     -d \'{"model":"meta-llama/Meta-Llama-3-8B-Instruct",\n'
        '          "messages":[{"role":"user","content":"hello"}],"max_tokens":8}\'\n'
        '# {"id":"chatcmpl-...","choices":[{"message":{"content":"Hi!"...}}],...}\n'
        "\n"
        "qdel 1234567                           # tear down"
    )
)
blocks.append(
    body_par(
        "The configuration it references: Llama-3-8B on two nodes (24 replicas) behind "
        "HAProxy. model_storage_path (your model directory on the shared file system) and "
        "local_stage_path (node-local staging) are typically the only fields that vary per "
        "user.",
        after=60,
    )
)
blocks.append(
    code_block(
        "# my_config.yaml\n"
        "num_nodes: 2\n"
        "ray_port: 6379\n"
        "node_cpus: 64\n"
        "model_storage_path: /lus/flare/projects/<PROJECT>/<user>/models\n"
        "local_stage_path: /tmp/hf_home\n"
        "num_gpus_per_node: 12\n"
        "models:\n"
        "  - model_id: meta-llama/Meta-Llama-3-8B-Instruct\n"
        "    tensor_parallel_size: 1\n"
        "    pipeline_parallel_size: 1\n"
        "    max_model_len: 4096\n"
        "    size: 8\n"
        "gateway:\n"
        "  kind: haproxy\n"
        "  port: 4001\n"
        "  backend_port: 8000\n"
        "  options: {balance: leastconn, maxconn: 8000}"
    )
)
blocks.append(
    callout(
        "Learn more:",
        "the README and docs/usage.md cover submission and --dry-run previews, docs/api.md "
        "lists the installed commands (including exaserve-launch-cluster for interactive "
        "allocations), and examples/config.reference.yaml shows the commonly used fields; "
        "src/exaserve/plan/compiler.py defines every accepted key.",
        LEARN_BG,
    )
)

# 5 Scaling
blocks.append(heading(5, "Measured scaling on Aurora"))
blocks.append(
    body_par(
        "The published evaluations span 1–256 Aurora nodes and were made on earlier "
        "snapshots of this code; the current tree has not been re-measured at that scale. "
        "These measurements describe the tested workloads, runtime configurations and "
        "gateway modes; individual fixes have their own verification coverage. "
        "Production-release admission remains artifact-specific and is recorded in the "
        "hardening status.",
        after=80,
    )
)
blocks.append(bold_lead("Front-end proxy at scale"))
blocks.append(
    body_par(
        "All client traffic enters through the head-node proxy. Non-streaming completions "
        "scale nearly linearly through a single HAProxy — 27.1k QPS with Llama-3-8B "
        "at 256 nodes / 3,072 single-tile replicas, 0.04% errors (0.0% as rounded in the "
        "paper). Streaming (SSE) is harder on "
        "a centralized front end: the per-token delivery path saturates the head node’s "
        "network at large node counts, so requests still complete but slowly — streaming "
        "throughput plateaus around 4.7k QPS from 128 nodes, and p99 end-to-end "
        "latency reaches 17 s at 256 nodes while non-streaming p99 stays near 2 s at every "
        "scale. Budget streaming capacity per proxy and prefer non-streaming completions at "
        "extreme scale.",
        after=60,
    )
)
blocks.append(
    figure(
        "fig1_proxy_scaling.png",
        "Fig. 2 of the paper, from its arXiv source: weak scaling, 1–256 nodes (Llama-3-8B, "
        "64 in / 64 out, 110 QPS/node offered), successful throughput and attainment of the "
        "two SLO components (P99 TBT ≤ 250 ms, TTFT ≤ 2 s) per front end, streaming (solid) "
        "vs non-streaming (dashed). Non-streaming HAProxy scales near-linearly; streaming "
        "through any centralized proxy plateaus or collapses. “Direct” is the benchmark-only "
        "backend-isolation diagnostic. The TTFT panel lacks Envoy's 256-node streaming point "
        "because of a plotting defect since fixed in eval/plot.",
        7.0,
    )
)
blocks.append(
    callout(
        "Note:",
        "for benchmarking only, the harness’s client can bypass the proxy and dispatch "
        "to per-node endpoints (client.dest: direct in a spec) to measure backend capacity "
        "without a front end — backends themselves scale linearly to 256 nodes when the "
        "proxy is bypassed. This mode exposes one endpoint per node and is not a deployment "
        "path.",
        NOTE_BG,
    )
)
blocks.append(bold_lead("Multi-node models"))
blocks.append(
    body_par(
        "Models larger than a node are served with pipeline parallelism across node pairs "
        "(Llama-3.1-405B: TP8 within a node × PP2 across two nodes). Shard-aware staging "
        "gives each pipeline stage only its own weight shard (~380 GiB, which fits node-local "
        "tmpfs) and pins each replica to its nodes. The 405B numbers quoted here are "
        "streaming: at a "
        "fixed per-replica offered rate, direct dispatch (the routing-free reference) grows "
        "aggregate successful throughput from 0.7 QPS at 2 replicas to 31.0 QPS at 128 "
        "replicas (4 to 256 nodes), a 67% weak-scaling efficiency vs the 4-node base. Through "
        "a single HAProxy the service stays within about 5% of direct dispatch through 16 "
        "replicas (4.7 against 4.9 QPS), falls behind from 32 replicas (8.7 against 10.3 "
        "QPS), and completes 22.9 QPS at 0.3% errors (50% efficiency) at 128 replicas. "
        "These are the corrected values: the paper's Fig. 5 plots three points from runs "
        "later excluded (see the caption), and its text quotes one of them (HAProxy 4.1 "
        "against 4.9 QPS at 16 replicas) to say HAProxy falls behind from 16 replicas. "
        "The paper attributes the remaining efficiency loss to "
        "requests still draining at the end of the fixed measurement window, not to "
        "routing. Non-streaming 405B runs through HAProxy, recorded later on a different "
        "snapshot and settings, are not summarized here.",
        after=60,
    )
)
blocks.append(
    figure(
        "fig7_pp405b.png",
        "Fig. 5 of the paper, from its arXiv source: Llama-3.1-405B (TP8 × PP2) weak "
        "scaling, 2–128 replicas at a fixed offered rate per replica; point labels give "
        "successful throughput and weak-scaling efficiency vs the 4-node base. Three points "
        "come from runs later excluded because they attached the deployment to a 256-node "
        "Ray cluster: HAProxy at 32 and 64 nodes (4.1 and 5.9 QPS; corrected 4.7 and 8.7) "
        "and direct dispatch at 64 nodes (10.6; corrected 10.3). The corrected values are "
        "in eval/plot/pp405b_legacy_evidence.yaml.",
        5.2,
    )
)
blocks.append(bold_lead("Robustness across workloads and models"))
blocks.append(
    body_par(
        "Holding the 8B baseline fixed and varying one axis at a time (each row’s offered "
        "rate pinned at 90% of its single-node saturation), SLO attainment — the fraction "
        "of requests meeting TTFT ≤ 2 s and P99 TBT ≤ 250 ms — holds at 64 nodes for "
        "long-context and moderate-rate workloads and for the 120B model. The two rows that "
        "degrade (the short/high-rate baseline and Poisson arrivals at the same mean) lose "
        "their latency margin at the saturation knee once 64 nodes share the streaming path: "
        "the failure is load-shape specific, not model- or workload-specific.",
        after=60,
    )
)
blocks.append(
    data_table(
        [
            ["Perturbation", "attain (N=1)", "attain (N=64)", "Δ"],
            ["(baseline) 8B, 64/64, fixed-interval", "0.94", "0.65", "−0.29"],
            ["Workload: ShareGPT 2K/2K", "1.00", "0.98", "−0.02"],
            ["Workload: ShareGPT 4K/4K", "1.00", "1.00", "0.00"],
            ["Workload: Code (HumanEval)", "1.00", "1.00", "0.00"],
            ["Workload: Chat (ShareGPT natural)", "0.99", "0.99", "0.00"],
            ["Workload: Summarization", "1.00", "1.00", "0.00"],
            ["Model: 120B (TP=8, rate 9)", "0.98", "0.97", "−0.01"],
            ["Arrival: Poisson", "0.92", "0.60", "−0.32"],
            ["Arrival: BurstGPT trace †", "0.46", "0.46", "0.00"],
        ],
        [4424, 2000, 2000, 1800],
    )
)
blocks.append(
    par(
        run(
            "† BurstGPT replays a fixed total arrival rate not scaled by N, so its N=64 cell is "
            "not a weak-scaling stress; reported for completeness.",
            sz=16,
            color=GRAYTXT,
        ),
        after=100,
    )
)
blocks.append(bold_lead("Steady-state serving vs. startup time"))
blocks.append(
    body_par(
        "Everything above is steady-state serving, measured after the cluster reports ready. "
        "Cluster bring-up behaves differently: it does not scale, and this is Ray’s key "
        "limitation at HPC scale. Model staging (~50 s for the 8B model), Ray cluster start "
        "(~45 s), and first-request warm-up (~8 s) are roughly flat in node count, but "
        "with one Serve application per node, as in the paper, Ray Serve’s serve.run phase "
        "grows superlinearly — 154 s at 64 nodes, 456 s at 128, and 1,767 s (about 30 min) "
        "at 256 — and a 512-node bring-up of that layout fails outright. The growth is "
        "concentrated in the proxy readiness wait: on every deployment broadcast, every "
        "Ray Serve proxy resolves every replica handle against the Ray control store (GCS), "
        "work that is quadratic in node count and reaches 1.38 million GCS lookups at 256 "
        "nodes. Budget job walltime as bring-up plus serving window (405B weight loading "
        "adds more), and reuse a running cluster across experiments where possible."
    )
)
blocks.append(bold_lead("Plan-bound validation controls"))
blocks.append(
    body_par(
        "These controls are compiled into the immutable deployment plan; ambient environment "
        "variables do not select a different production topology:",
        after=60,
    )
)
blocks.append(
    data_table(
        [
            ["Plan field", "Effect"],
            [
                "engine: vllm",
                "The Aurora production SiteProfile rejects unqualified engines such as SGLang",
            ],
            [
                "runtime.pp_shard_aware: true",
                "Shard-aware multi-node pipeline-parallel staging and node-pinned replicas "
                "(405B-class models)",
            ],
            [
                "runtime.null_compute: true",
                "Skip the engine and simulate latency — control-plane stress tests",
            ],
            [
                "runtime.clean_stage: true",
                "Run a non-destructive all-rank cache reconciliation barrier before staging "
                "(not a cold-cache guarantee)",
            ],
        ],
        [3300, 6924],
    )
)
blocks.append(
    body_par(
        "Historical scale cliffs are catalogued in docs/KNOWN_ISSUES.md. The compatibility "
        "profile activates only version-pinned targeted changes and every required process "
        "attests the result before READY."
    )
)
blocks.append(
    callout(
        "Portability.",
        "The code has scheduler, gateway, vendor, and engine interfaces, but interfaces are not "
        "support claims. The default Aurora SiteProfile admits only PBS, XPU, vLLM, and "
        "HAProxy as candidate dimensions, and production submission currently fails closed. "
        "Slurm/PSI-J, CUDA/ROCm, SGLang, streaming, direct exposure, and alternate "
        "gateways fail closed or require explicit validation-only plans until separately proven.",
        NOTE_BG,
    )
)

# 6 Clients
blocks.append(heading(6, "Serving agents and OpenAI-compatible clients"))
blocks.append(
    body_par(
        "The deployment exposes the standard OpenAI API, so any compatible client works unchanged "
        "— LangChain’s ChatOpenAI, Academy LLM agents, litellm, or the openai SDK — "
        "by pointing the usual environment variables at the service URL. This makes the framework "
        "the self-hosted, on-machine complement to a hosted inference gateway: the same agent "
        "code runs against either.",
        after=60,
    )
)
blocks.append(
    code_block("export OPENAI_BASE_URL=http://<head_node>:4001/v1\nexport OPENAI_API_KEY=EMPTY")
)
blocks.append(
    body_par(
        "The current HAProxy exposure is trusted-allocation/internal and has no public-network "
        "authentication claim. Do not expose it outside that boundary. LiteLLM is validation-only."
    )
)

# 7 Examples and Resources
blocks.append(heading(7, "Examples and Resources"))
blocks.append(
    body_par(
        "Runnable configurations and benchmark specifications live in the repository; code is "
        "linked rather than copied here. Paths are relative to "
        "github.com/AI-ModCon/exaserve."
    )
)
blocks.append(
    data_table(
        [
            ["Resource", "Location"],
            ["Source code", "github.com/AI-ModCon/exaserve"],
            [
                "Documentation",
                "README.md — install and configuration; docs/api.md — console-script reference",
            ],
            [
                "Machine-actionable card",
                "docs/exaserve.md — markdown version of this card for coding agents",
            ],
            [
                "Deployment templates",
                "examples/ — HAProxy, LiteLLM, and a reference configuration of the commonly "
                "used fields",
            ],
            [
                "Benchmark specs",
                "eval/specs/refcard/ — the smoke, weak-scaling, and 405B pipeline-parallel "
                "specs referenced in this card",
            ],
            [
                "Scaling analyses",
                "docs/operations_handbook.md and docs/KNOWN_ISSUES.md — limits, root causes, fixes",
            ],
        ],
        [2800, 7424],
    )
)

# 8 Citation
blocks.append(heading(8, "Citation"))
blocks.append(
    body_par(
        "The system and its 1–256-node evaluation are described in ExaServe: Large-Scale "
        "LLM Serving on Exascale HPC Systems, arXiv:2609.10812. "
        "https://arxiv.org/abs/2609.10812",
        after=60,
    )
)
blocks.append(
    code_block(
        "@misc{wang2026exaserve,\n"
        "    title = {ExaServe: Large-Scale LLM Serving on\n"
        "             Exascale HPC Systems},\n"
        "    author = {Wenyi Wang and Shu Shi and Yadu Babuji and\n"
        "              Ian Foster and Kyle Chard},\n"
        "    year = {2026},\n"
        "    eprint = {2609.10812},\n"
        "    archivePrefix = {arXiv},\n"
        "    primaryClass = {cs.DC},\n"
        "    doi = {10.48550/arXiv.2609.10812},\n"
        "    url = {https://arxiv.org/abs/2609.10812}\n"
        "}"
    )
)

# ------------------------------------------------------------- assemble docx
with zipfile.ZipFile(SRC) as z:
    old_doc = z.read("word/document.xml").decode("utf-8")

sectpr = re.search(r"<w:sectPr.*?</w:sectPr>", old_doc, re.S).group(0)
header = old_doc[: old_doc.index("<w:body>") + len("<w:body>")]
new_doc = header + "".join(blocks) + sectpr + "</w:body></w:document>"


def _drop_unused_hyperlinks(rels: str, document: str) -> str:
    """Drop the template's hyperlink relationships that the card never references."""

    def keep(match: re.Match) -> str:
        element = match.group(0)
        rid = re.search(r'Id="([^"]+)"', element)
        hyperlink = re.search(r'Type="[^"]*/hyperlink"', element)
        if hyperlink and rid and f'r:id="{rid.group(1)}"' not in document:
            return ""
        return element

    return re.sub(r"<Relationship\b[^>]*/>", keep, rels)


rel_entries = "".join(
    f'<Relationship Id="{rid}" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
    f'Target="{target}"/>'
    for target, _, rid in _images
)

OUT.parent.mkdir(parents=True, exist_ok=True)
with tempfile.NamedTemporaryFile(
    prefix=f".{OUT.name}.", suffix=".tmp", dir=OUT.parent, delete=False
) as temporary:
    temporary_path = Path(temporary.name)
try:
    with (
        zipfile.ZipFile(SRC) as zin,
        zipfile.ZipFile(temporary_path, "w", zipfile.ZIP_DEFLATED) as zout,
    ):
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                data = new_doc.encode("utf-8")
            elif item.filename == "word/_rels/document.xml.rels":
                rels = _drop_unused_hyperlinks(data.decode("utf-8"), new_doc)
                data = rels.replace("</Relationships>", rel_entries + "</Relationships>").encode(
                    "utf-8"
                )
            elif item.filename.startswith("word/footer"):
                data = data.replace(b"Academy", b"ExaServe")
            zout.writestr(item, data)
        for target, src, _ in _images:
            # A fixed timestamp keeps regeneration byte-for-byte reproducible.
            info = zipfile.ZipInfo(f"word/{target}", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zout.writestr(info, src.read_bytes())
    os.replace(temporary_path, OUT)
finally:
    temporary_path.unlink(missing_ok=True)

print("wrote", OUT, f"({len(_images)} figures embedded)")
