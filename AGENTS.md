## Ansible Local Temp

When running Ansible commands from this project, set `ANSIBLE_LOCAL_TEMP=/tmp`.

Reason: some environments hit permission errors under the default local temp path.

Example:

```bash
ANSIBLE_LOCAL_TEMP=/tmp ansible-playbook --syntax-check playbooks/opencode.yml
```
