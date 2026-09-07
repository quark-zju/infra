# Idempotent-run benchmark results

## Result

On 2026-09-07, against the already-converged `opi` host, the experimental
pyinfra port had a median wall time of **21.64 seconds**, versus **142.55
seconds** for Ansible. That is a **6.59x speedup** and an **84.8% reduction** in
median elapsed time.

| Iteration | Ansible (s) | pyinfra (s) | Speedup |
|---:|---:|---:|---:|
| 1 | 142.55 | 21.64 | 6.59x |
| 2 | 140.18 | 49.64 | 2.82x |
| 3 | 153.58 | 19.34 | 7.94x |
| Median | **142.55** | **21.64** | **6.59x** |
| Mean | 145.44 | 30.21 | 4.81x |

The pyinfra second run was an outlier. Both implementations contact the remote
Git repository for the DSH plugins on every run, so network latency remains in
the supposedly idle path. Reporting the median keeps that one sample visible
without allowing it to dominate the comparison.

## Method

- Controller: macOS, Ansible Core 2.21.1, pyinfra 3.10.0.
- Target: the inventory host `opi`, connected as root over SSH.
- The existing Ansible playbook was run to convergence first and reported
  `changed=0`.
- The pyinfra deploy was then run and its Jinja rendering was adjusted to be
  byte-compatible with Ansible's systemd unit output.
- A normal Ansible run immediately after pyinfra reported `changed=0`. This
  cross-idempotence check matters: it proves the faster implementation did not
  merely skip work by managing a different final state.
- `benchmark.sh` alternated Ansible then pyinfra for three iterations and used
  `time.monotonic_ns()` around the complete processes, including startup, SSH,
  fact collection and teardown.
- All three measured Ansible runs reported `ok=63 changed=0 skipped=30`.

Raw logs are intentionally excluded from Git because they contain host details.
The committed table above is transcribed from `results/times.csv`:

```csv
tool,iteration,seconds
ansible,1,142.54976225
pyinfra,1,21.639963792
ansible,2,140.182068333
pyinfra,2,49.639503084
ansible,3,153.581700875
pyinfra,3,19.343614
```

## Why pyinfra is faster here

The Ansible role executes 63 successful tasks on its no-change path. Many are
separate `stat`, `command`, module, loop-item, or fact-setting invocations. Even
with SSH pipelining enabled, their controller/module startup and round-trip
costs accumulate. The pyinfra deploy batches its generated shell commands much
more aggressively and represents the same default path as 45 operations.

This does not mean every pyinfra `Success` row changed the host. Its generic
shell operation conservatively reports success for guarded `chmod`, linger,
Git pull, and wrapper commands. Cross-checking with Ansible's `changed=0` is the
stronger test of actual state stability.

## Port coverage and limitations

The experiment covers the role's current default path: packages, MOTD scripts,
Node.js, Neovim, pnpm, DeepSeek Harness and plugins, the DSH patch, Codex,
repositories, Rust/leash, dotfile links, and OpenCode/DSH systemd units.

It deliberately does not yet replace the production playbook:

- Kimi's non-default enabled path is not ported; the default disabled state is.
- Ansible Vault loading is not ported. A pre-existing
  `/etc/opencode/opencode.env` is preserved, matching the no-password behavior
  used in this benchmark.
- There is no handler abstraction yet. A unit content change is installed and
  systemd is reloaded, but already-running services are not automatically
  restarted as Ansible handlers would do.
- Several guarded shell operations are operationally idempotent but do not give
  pyinfra perfectly precise changed reporting.
- Only an already-converged run was benchmarked. First-install speed and failure
  recovery need a disposable ARM64 target before considering migration.

## Recommendation

The result is large enough to justify continuing the experiment. The next step
should be to add change-aware service restarts, secret input support, and a
disposable-host first-install test. Until those are complete, keep Ansible as
the authoritative implementation and use this directory as a performance and
design prototype rather than production replacement.
