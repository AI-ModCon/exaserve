SITE_OVERRIDES = {
    # Replace these absolute paths with your site's approved storage/runtime.
    # See docs/getting_started.md; no maintainer-private scripts are required
    # for ordinary Ray eval jobs. Allocation campaigns have a separate bootstrap.
    # This file configures evaluation only. Serving reads the environment:
    # exaserve-serve-submit needs EXASERVE_ENV_SCRIPT_AURORA, and it and
    # exaserve-launch-cluster need EXASERVE_PROJECT_ROOT (or
    # EXASERVE_MODEL_STORAGE_PATH).
    "project_root": "/lus/flare/projects/YOUR_PROJECT",
    "user_data_root": "/lus/flare/projects/YOUR_PROJECT/YOUR_USER/data",
    "model_storage_path": "/lus/flare/projects/YOUR_PROJECT/YOUR_USER/models",
    "env_script_aurora": "/absolute/path/to/environment.sh",
    "snapshot_dir": "/lus/flare/projects/YOUR_PROJECT/YOUR_USER/snapshots",
    "bench_results_dir": "/lus/flare/projects/YOUR_PROJECT/YOUR_USER/bench_results",
    # Only needed for an explicitly authorized LiteLLM gateway:
    # "litellm_python_path": "/absolute/path/to/litellm-runtime/bin/python3",
    # "pbs_mail_user": "your_user@example.com",
}
