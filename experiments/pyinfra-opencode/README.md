# Experimental pyinfra port of the OpenCode role

This directory ports the **default** execution path of `playbooks/opencode.yml`
to pyinfra 3.10.0 for a measured idempotent-run comparison. It manages the base
packages, MOTD scripts, Node.js, Neovim, pnpm, DeepSeek Harness and plugins,
Codex, repositories, Rust/leash, dotfile links, and the OpenCode/DSH systemd
units. The non-default Kimi installation path and Ansible Vault decryption are
not implemented; a pre-existing `/etc/opencode/opencode.env` is preserved.

Run it from the repository root:

```sh
pyinfra experiments/pyinfra-opencode/inventory.py \
  experiments/pyinfra-opencode/deploy.py --limit opi -y
```

For alternating idempotent runs of both implementations:

```sh
RUNS=3 experiments/pyinfra-opencode/benchmark.sh
```

Raw logs and `times.csv` are written under `results/`, which is ignored. See
`RESULTS.md` for the environment, measurements, limitations, and conclusion.

See `ANALYSIS.zh.md` for a Chinese-language analysis of pyinfra's two-phase
semantics, the OpenCode role's runtime dependencies, and the feasibility and
estimated benefit of single-host DAG parallelism. `profile_stages.py` can be
used to measure the wall time of pyinfra's Setup, Connect, Prepare, and Execute
stages without changing the deployment.
