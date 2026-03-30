# infra

Ansible repo for managing personal machines like `opi`, and later VPS or laptops.

## Layout

- `inventory/production.yml`: current inventory
- `playbooks/opencode.yml`: installs and manages the OpenCode service on `opi`
- `roles/opencode/`: npm install, service account, env file, and systemd unit

## Common commands

Check connectivity:

```bash
ansible opi -m ping
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

Create the variable file from the example:

```bash
mkdir -p group_vars/opi
cp group_vars/opi/vault.yml.example group_vars/opi/vault.yml
```

Edit the file before encrypting it:

```bash
$EDITOR group_vars/opi/vault.yml
```

Encrypt it:

```bash
ansible-vault encrypt group_vars/opi/vault.yml
```

Edit an encrypted file later:

```bash
ansible-vault edit group_vars/opi/vault.yml
```

View it without modifying:

```bash
ansible-vault view group_vars/opi/vault.yml
```

Rekey it:

```bash
ansible-vault rekey group_vars/opi/vault.yml
```

If you prefer a local vault password file, save it outside the repo or in `.vault_pass.txt` and keep it untracked:

```bash
ansible-playbook playbooks/opencode.yml --vault-password-file .vault_pass.txt
```

## Notes

- `opencode` runs as its own system user and group
- service home is `/home/opencode`
- service env lives at `/etc/opencode/opencode.env`
- default web bind is `0.0.0.0:4096`
