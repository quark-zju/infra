# infra

Ansible repo for personal configurations.

## Common commands

```bash
# Update configs of the local machine (macOS or Linux)
# (consider running `sudo -v` first to update sudo timestamp)
ansible-playbook playbooks/local.yml

# Update configs of remote Linux hosts
# (use --limit a:b to select hosts)
ansible-playbook playbooks/linux-hardening.yml
```

----

## What Each Command Changes

| Run from | Command | Affects | What changes |
| --- | --- | --- | --- |
| The machine you want to configure | `ansible-playbook playbooks/local.yml` | `localhost`, through the `local` inventory group | Always applies the local dotfiles role on macOS/Linux: clones or updates `~/src/dotfiles`, writes `~/.gitconfig.local`, writes dotfiles Cargo config into `~/.cargo/config.toml`, and manages dotfile symlinks including shared AGENTS.md links for opencode, Codex, and Zed. On macOS it also installs Homebrew packages including Neovim, Zed, Hammerspoon, pyenv, ripgrep, and JetBrains Maple Mono NF; configures GUI apps to inherit the current PATH when run with sudo access; disables natural scrolling globally; sets Safari's quit shortcut to Command+Shift+Q; and installs the Hammerspoon config. Use `-K` if Ansible needs to prompt for the sudo password. On Linux it also applies the Linux hardening role with `become`. |
| Any machine that can SSH to all `linux` inventory hosts | `ansible-playbook playbooks/linux-hardening.yml` | `x13`, `sf`, `hz`, and `opi` | Applies Linux hardening as root: writes the risky kernel module blacklist and hardening sysctl file. |
| Any machine that can SSH to one Linux host | `ansible-playbook playbooks/linux-hardening.yml --limit opi` | Only `opi` | Same Linux hardening role, limited to one host. Change `opi` to another inventory hostname as needed. |
| Any machine that can SSH to `x13` and prompt for sudo | `ansible-playbook playbooks/linux-hardening.yml --limit x13 -K` | Only `x13` | Same Linux hardening role, with `-K` prompting for the sudo password. |
| Any machine that can SSH to the `macos` inventory host | `ansible-playbook playbooks/macos.yml` | `mac` | Applies only the shared macOS role over SSH: installs Homebrew packages including Neovim, Zed, Hammerspoon, pyenv, ripgrep, and JetBrains Maple Mono NF; configures GUI apps to inherit the current PATH when run with sudo access; disables natural scrolling globally; sets Safari's quit shortcut to Command+Shift+Q; and installs the Hammerspoon config. Use `-K` if Ansible needs to prompt for the sudo password. It does not run the local dotfiles role. |
| Any machine that can SSH to `opi` as root and read the vault secret | `ansible-playbook playbooks/opencode.yml --ask-vault-pass` | `opi` | Installs and manages the OpenCode and Kimi web services: npm packages, service user, dotfiles/leash repos, Rust toolchain, config symlinks, `/etc/opencode/opencode.env`, systemd units, and running services. |
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
| `ansible opi -a 'systemctl status kimi --no-pager'` | `opi` | Runs a read-only Kimi service status command on `opi`. |
| `ansible opi -b -a 'systemctl restart opencode'` | `opi` | Runs exactly that command with privilege escalation. It restarts the service but does not update packages, configs, vault-backed env files, or systemd units. |
| `ansible opi -a 'ss -ltnp \| grep 4096'` | `opi` | Checks whether something is listening on port `4096`. |
| `ansible opi -a 'ss -ltnp \| grep 58627'` | `opi` | Checks whether Kimi web is listening on port `58627`. |
| `ansible opi -b -a 'journalctl -u opencode -n 50 --no-pager'` | `opi` | Reads recent OpenCode service logs. |
| `ansible opi -b -a 'journalctl -u kimi -n 50 --no-pager'` | `opi` | Reads recent Kimi web service logs, including the startup bearer-token URL. |

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

- `ansible.cfg` keeps controller temporary files under `/tmp` so local macOS runs do not depend on `~/.ansible/tmp` being writable
- `opencode` and `kimi` run as the dedicated `opencode` system user and group
- linger is enabled for the `opencode` user so `/run/user/<uid>` remains available without an interactive login
- service home is `/home/opencode`
- the root-only service environment lives at `/etc/opencode/opencode.env`; Kimi reuses the OpenCode server password and disables telemetry
- OpenCode binds to `0.0.0.0:4096` and Kimi web binds to `0.0.0.0:58627` by default
- both web services run inside the leash sandbox
