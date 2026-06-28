# infra

Ansible repo for managing personal machines like `opi`, `x13`, macOS, and other hosts.

## Layout

- `inventory/production.yml`: current inventory and groups
- `playbooks/local.yml`: local machine entry point that dispatches by detected OS
- `playbooks/linux-hardening.yml`: baseline Linux security hardening for the `linux` group
- `playbooks/macos.yml`: SSH-managed macOS entry point for shared macOS baseline
- `playbooks/opencode.yml`: installs and manages the OpenCode service on `opi`
- `roles/dotfiles/`: local macOS/Linux dotfiles clone, symlinks, and Git identity
- `roles/linux_hardening/`: risky module blacklist + scoped ptrace policy
- hardening sysctl file: `/etc/sysctl.d/99-linux-hardening.conf`
- `roles/macos/`: shared macOS tasks, including Homebrew packages, system scroll direction, and Hammerspoon configuration
- `roles/opencode/`: npm install, service account, env file, and systemd unit

## What Each Command Changes

| Run from | Command | Affects | What changes |
| --- | --- | --- | --- |
| The machine you want to configure | `ansible-playbook playbooks/local.yml` | `localhost`, through the `local` inventory group | Always applies the local dotfiles role on macOS/Linux: clones or updates `~/src/dotfiles`, writes `~/.gitconfig.local`, and manages dotfile symlinks. On macOS it also installs Homebrew packages including Neovim, Zed, Hammerspoon, pyenv, ripgrep, and JetBrains Maple Mono NF; disables natural scrolling globally; and installs the Hammerspoon config. On Linux it also applies the Linux hardening role with `become`. |
| Any machine that can SSH to all `linux` inventory hosts | `ansible-playbook playbooks/linux-hardening.yml` | `x13`, `sf`, `hz`, and `opi` | Applies Linux hardening as root: writes the risky kernel module blacklist and hardening sysctl file. |
| Any machine that can SSH to one Linux host | `ansible-playbook playbooks/linux-hardening.yml --limit opi` | Only `opi` | Same Linux hardening role, limited to one host. Change `opi` to another inventory hostname as needed. |
| Any machine that can SSH to `x13` and prompt for sudo | `ansible-playbook playbooks/linux-hardening.yml --limit x13 -K` | Only `x13` | Same Linux hardening role, with `-K` prompting for the sudo password. |
| Any machine that can SSH to the `macos` inventory host | `ansible-playbook playbooks/macos.yml` | `mac` | Applies only the shared macOS role over SSH: installs Homebrew packages including Neovim, Zed, Hammerspoon, pyenv, ripgrep, and JetBrains Maple Mono NF; disables natural scrolling globally; and installs the Hammerspoon config. It does not run the local dotfiles role. |
| Any machine that can SSH to `opi` as root and read the vault secret | `ansible-playbook playbooks/opencode.yml --ask-vault-pass` | `opi` | Installs and manages the OpenCode service: packages, service user, dotfiles/leash repos, Rust toolchain, config symlinks, `/etc/opencode/opencode.env`, systemd unit, and running service. |
| Any machine that can SSH to `opi` as root and read the vault secret | `ansible-playbook playbooks/opencode.yml --check --ask-vault-pass` | `opi`, in check mode | Dry-runs the OpenCode playbook where modules support check mode. Use this to preview likely changes, not as a perfect guarantee. |

Syntax checks only parse playbooks; they do not change target machines.

```bash
ansible-playbook --syntax-check playbooks/linux-hardening.yml
ansible-playbook --syntax-check playbooks/local.yml
ansible-playbook --syntax-check playbooks/macos.yml
ansible-playbook --syntax-check playbooks/opencode.yml
```

## `ansible` vs `ansible-playbook`

Use `ansible-playbook` to apply the configured roles above. It reads a playbook, gathers facts when the playbook asks for them, evaluates `when` conditions, loads roles, uses handlers, and applies the desired state described in this repo.

Use `ansible` for one-off ad-hoc commands. It targets hosts or groups from `inventory/production.yml`, but it does not automatically run this repo's playbooks or roles.

| Command | Affects | What happens |
| --- | --- | --- |
| `ansible linux -m ping` | `x13`, `sf`, `hz`, and `opi` | Runs only the `ping` module to test connectivity. No roles or config files are applied. |
| `ansible opi -a 'systemctl status opencode --no-pager'` | `opi` | Runs a read-only status command on `opi`. |
| `ansible opi -b -a 'systemctl restart opencode'` | `opi` | Runs exactly that command with privilege escalation. It restarts the service but does not update packages, configs, vault-backed env files, or systemd units. |
| `ansible opi -a 'ss -ltnp \| grep 4096'` | `opi` | Checks whether something is listening on port `4096`. |
| `ansible opi -b -a 'journalctl -u opencode -n 50 --no-pager'` | `opi` | Reads recent OpenCode service logs. |

If the goal is to converge a machine to the configuration in this repository, use `ansible-playbook`. If the goal is to inspect or poke a machine once, use `ansible`.

## ansible-vault

Keep secrets out of the repo in plaintext. The role expects `opencode_server_password`.

`ansible-vault` is recommended, not required. If `inventory/group_vars/opi_nodes/vault.yml` is kept out of Git, a plaintext file also works and Ansible will load it normally.

Create the variable file from the example:

```bash
mkdir -p inventory/group_vars/opi_nodes
cp inventory/group_vars/opi_nodes/vault.yml.example inventory/group_vars/opi_nodes/vault.yml
```

Edit the file before encrypting it:

```bash
$EDITOR inventory/group_vars/opi_nodes/vault.yml
```

Encrypt it:

```bash
ansible-vault encrypt inventory/group_vars/opi_nodes/vault.yml
```

If you keep it as plaintext instead, you can skip encryption and run the playbook without `--ask-vault-pass`.

Edit an encrypted file later:

```bash
ansible-vault edit inventory/group_vars/opi_nodes/vault.yml
```

View it without modifying:

```bash
ansible-vault view inventory/group_vars/opi_nodes/vault.yml
```

Rekey it:

```bash
ansible-vault rekey inventory/group_vars/opi_nodes/vault.yml
```

The role also supports the older repo-root path `group_vars/opi_nodes/vault.yml` for compatibility, but new files should go under `inventory/group_vars/`.

If you prefer a local vault password file, save it outside the repo or in `.vault_pass.txt` and keep it untracked:

```bash
ansible-playbook playbooks/opencode.yml --vault-password-file .vault_pass.txt
```

## Notes

- `ansible.cfg` keeps Ansible home plus controller and target temporary files under `/tmp` so local macOS runs do not depend on `~/.ansible` being writable
- `opencode` runs as its own system user and group
- service home is `/home/opencode`
- service env lives at `/etc/opencode/opencode.env`
- default web bind is `0.0.0.0:4096`
