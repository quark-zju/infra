# infra

Ansible repo for managing personal machines like `opi`, `x13`, macOS, and other hosts.

## Layout

- `inventory/production.yml`: current inventory and groups
- `playbooks/local.yml`: local machine entry point that dispatches by detected OS
- `playbooks/linux-hardening.yml`: baseline Linux security hardening for the `linux` group
- `playbooks/macos.yml`: SSH-managed macOS entry point, currently intentionally empty
- `playbooks/opencode.yml`: installs and manages the OpenCode service on `opi`
- `roles/linux_hardening/`: risky module blacklist + scoped ptrace policy
- hardening sysctl file: `/etc/sysctl.d/99-linux-hardening.conf`
- `roles/macos/`: placeholder for shared macOS tasks
- `roles/opencode/`: npm install, service account, env file, and systemd unit

## Common commands

Check connectivity:

```bash
ansible linux -m ping
```

Run the Linux hardening playbook:

```bash
ansible-playbook playbooks/linux-hardening.yml
```

Run hardening only for one host:

```bash
ansible-playbook playbooks/linux-hardening.yml --limit opi
```

Run hardening for the Linux laptop:

```bash
ansible-playbook playbooks/linux-hardening.yml --limit x13 -K
```

Run the SSH-managed macOS playbook:

```bash
ansible-playbook playbooks/macos.yml
```

Run the local machine playbook:

```bash
ansible-playbook playbooks/local.yml
```

Run the OpenCode playbook:

```bash
ansible-playbook playbooks/opencode.yml --ask-vault-pass
```

Dry-run the OpenCode playbook:

```bash
ansible-playbook playbooks/opencode.yml --check --ask-vault-pass
```

Syntax check:

```bash
ansible-playbook --syntax-check playbooks/linux-hardening.yml
ansible-playbook --syntax-check playbooks/local.yml
ansible-playbook --syntax-check playbooks/macos.yml
ansible-playbook --syntax-check playbooks/opencode.yml
```

Check service status:

```bash
ansible opi -a 'systemctl status opencode --no-pager'
```

Restart the service:

```bash
ansible opi -b -a 'systemctl restart opencode'
```

Check listening port:

```bash
ansible opi -a 'ss -ltnp | grep 4096'
```

View recent logs:

```bash
ansible opi -b -a 'journalctl -u opencode -n 50 --no-pager'
```

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
