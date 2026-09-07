"""Experimental pyinfra port of the default OpenCode Ansible role.

This intentionally targets the current default: DeepSeek enabled, Kimi disabled.
Run from the repository root with:
    pyinfra experiments/pyinfra-opencode/inventory.py \
      experiments/pyinfra-opencode/deploy.py --limit opi
"""

import json
import shlex
import sys
from pathlib import Path
from jinja2 import FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pyinfra import host
from pyinfra.facts.files import Directory, File
from pyinfra.facts.server import Command, Users
from pyinfra.operations import apt, files, server, systemd

from config import (
    CODEX_ARCHIVE, CODEX_BIN, CODEX_URL, DSH_DIR, DSH_PLUGINS_REPO,
    DSH_PROFILES, GROUP, HOME, NODE_ARCHIVE, NODE_BIN, NODE_DIR, NODE_URL,
    NVIM_ARCHIVE, NVIM_DIR, NVIM_URL, PACKAGES, REPOSITORIES, SRC,
    TEMPLATE_DATA, TEMPLATES, USER,
)


class AnsibleIncludeLoader(FileSystemLoader):
    """Match Ansible's handling of the trailing newline in included templates."""

    def get_source(self, environment, template):
        source, filename, uptodate = super().get_source(environment, template)
        if template == "network-access.conf.j2":
            source = source.removesuffix("\n")
        return source, filename, uptodate


def q(value):
    return shlex.quote(str(value))


def remote_exists(path):
    return host.get_fact(Command, command=f"test -e {q(path)}; printf $?").strip() == "0"


apt.packages(name="Install base packages", packages=PACKAGES, update=True)

for script in ("10-armbian-header", "15-ap-info", "20-ip-info", "30-armbian-sysinfo", "35-armbian-tips", "41-commands"):
    server.shell(
        name=f"Disable slow MOTD script {script}",
        commands=f"test ! -e /etc/update-motd.d/{script} || chmod a-x /etc/update-motd.d/{script}",
    )

files.directory(name="Ensure /opt exists", path="/opt", user="root", group="root", mode="755")
if not host.get_fact(File, path=f"{NODE_DIR}/bin/node"):
    files.download(name="Download Node.js", src=NODE_URL, dest=NODE_ARCHIVE, mode="644")
files.unarchive(name="Extract Node.js", src=NODE_ARCHIVE, dest="/opt", remote_src=True, creates=f"{NODE_DIR}/bin/node")
for binary in ("node", "npm", "npx"):
    files.link(name=f"Link {binary}", path=f"/usr/local/bin/{binary}", target=f"{NODE_BIN}/{binary}", force=True)

if not host.get_fact(File, path=f"{NVIM_DIR}/bin/nvim"):
    files.download(name="Download Neovim", src=NVIM_URL, dest=NVIM_ARCHIVE, mode="644")
files.unarchive(name="Extract Neovim", src=NVIM_ARCHIVE, dest="/opt", remote_src=True, creates=f"{NVIM_DIR}/bin/nvim")
files.link(name="Link Neovim", path="/usr/local/bin/nvim", target=f"{NVIM_DIR}/bin/nvim", force=True)

server.group(name="Ensure opencode group", group=GROUP, system=True)
server.user(name="Ensure opencode user", user=USER, group=GROUP, system=True, create_home=True, home=HOME, shell="/bin/zsh")
files.directory(name="Ensure opencode directories", path=HOME, user=USER, group=GROUP, mode="750")
for directory in (f"{HOME}/.local/bin", SRC, f"{HOME}/.config"):
    files.directory(path=directory, user=USER, group=GROUP, mode="750")
server.shell(name="Enable linger", commands=f"test -e /var/lib/systemd/linger/{USER} || loginctl enable-linger {USER}")

pnpm_version = host.get_fact(Command, command=f"PATH={q(NODE_BIN)}:$PATH pnpm --version 2>/dev/null || true").strip()
if not pnpm_version.startswith("9."):
    server.shell(name="Install pnpm 9", commands=f"PATH={q(NODE_BIN)}:$PATH npm install -g pnpm@9")

files.directory(name="Ensure DeepSeek directory", path=DSH_DIR, user=USER, group=GROUP, mode="750")
dsh_present = remote_exists(f"{DSH_DIR}/node_modules/@deepseek-ai/dsh")
if not dsh_present:
    server.shell(name="Install DeepSeek Harness", commands=f"runuser -u {USER} -- env HOME={q(HOME)} /usr/local/bin/pnpm add --dir {q(DSH_DIR)} --save-exact @deepseek-ai/dsh")
files.directory(path=f"{DSH_PLUGINS_REPO.rsplit('/', 1)[0]}", user=USER, group=GROUP, mode="750")
if host.get_fact(Directory, path=f"{DSH_PLUGINS_REPO}/.git"):
    server.shell(name="Update DeepSeek plugins", commands=f"runuser -u {USER} -- git -C {q(DSH_PLUGINS_REPO)} pull --ff-only")
else:
    server.shell(name="Clone DeepSeek plugins", commands=f"runuser -u {USER} -- git clone https://github.com/quark-zju/dsh-plugins {q(DSH_PLUGINS_REPO)}")

for profile, package, source in (
    ("web", "dsh-bill", f"{DSH_PLUGINS_REPO}/dsh-bill"),
    ("web", "dsh-web-notification", f"{DSH_PLUGINS_REPO}/dsh-web-notification"),
):
    package_json = f"{DSH_PROFILES}/{profile}/package.json"
    check = "const f=require('fs'),p=JSON.parse(f.readFileSync(process.argv[1])),n=process.argv[2];process.exit(p.dependencies?.[n]||p.devDependencies?.[n]||p.optionalDependencies?.[n]?0:1)"
    present = host.get_fact(Command, command=f"test -f {q(package_json)} && /usr/local/bin/node -e {q(check)} {q(package_json)} {q(package)}; printf $?").strip() == "0"
    if not present:
        server.shell(name=f"Install DSH plugin {package}", commands=f"runuser -u {USER} -- env HOME={q(HOME)} /usr/local/bin/pnpm --dir {q(DSH_DIR)} exec dsh plugin --profile {q(profile)} add -w {q(source)}")

marker = f"{DSH_DIR}/.patched"
if not dsh_present:
    files.file(name="Invalidate stale DSH patch marker", path=marker, present=False)
if not dsh_present or not host.get_fact(File, path=marker):
    patch_script = r'''import pathlib,re
root=pathlib.Path("''' + DSH_DIR + r'''/node_modules/.pnpm")
pat=re.compile(r"(?ms)^([ \t]*)function isLoopbackHostname\(hostname\) \{\n.*?^\1\}")
for path in root.rglob("*.js"):
    text=path.read_text(errors="surrogateescape")
    if "function isLoopbackHostname(hostname) {" in text:
        path.write_text(pat.sub(lambda m: m.group(1)+"function isLoopbackHostname(hostname) {\n"+m.group(1)+"\treturn true;\n"+m.group(1)+"}",text),errors="surrogateescape")'''
    server.shell(name="Patch DSH loopback detection", commands=f"python3 -c {q(patch_script)} && install -o {USER} -g {GROUP} -m 0644 /dev/null {q(marker)}")

wrapper = "#!/bin/sh\nexec /usr/local/bin/pnpm --dir /home/opencode/.deepseek-harness exec dsh \"$@\""
server.shell(name="Install dsh wrapper", commands=f"printf %s {q(wrapper)} | install -o {USER} -g {GROUP} -m 0750 /dev/stdin {HOME}/.local/bin/dsh")

if not host.get_fact(File, path=CODEX_BIN):
    files.download(name="Download Codex", src=CODEX_URL, dest=CODEX_ARCHIVE, mode="644")
    server.shell(name="Extract Codex", commands=f"zstd -d -f {q(CODEX_ARCHIVE)} -o {q(CODEX_BIN)}")
files.file(name="Set Codex permissions", path=CODEX_BIN, user=USER, group=GROUP, mode="755")

for source, destination in REPOSITORIES:
    if not host.get_fact(Directory, path=f"{destination}/.git"):
        server.shell(name=f"Clone {destination}", commands=f"runuser -u {USER} -- git clone {q(source)} {q(destination)}")

rust_ok = host.get_fact(Command, command=f"runuser -u {USER} -- env HOME={q(HOME)} /usr/bin/rustup run stable rustc --version >/dev/null 2>&1; printf $?").strip() == "0"
if not rust_ok:
    server.shell(name="Install stable Rust", commands=f"runuser -u {USER} -- env HOME={q(HOME)} /usr/bin/rustup toolchain install stable --profile minimal")
if not host.get_fact(File, path=f"{HOME}/.cargo/bin/leash"):
    server.shell(name="Build leash", commands=f"cd {HOME}/src/leash && runuser -u {USER} -- env HOME={q(HOME)} /usr/bin/rustup run stable cargo install --path .")

links = {
    f"{HOME}/.gitconfig": f"{HOME}/src/dotfiles/.gitconfig",
    f"{HOME}/.zshrc": f"{HOME}/src/dotfiles/.zshrc",
    f"{HOME}/.config/zsh": "../src/dotfiles/.config/zsh",
    f"{HOME}/.config/git-hooks": f"{HOME}/src/dotfiles/.config/git-hooks",
}
files.directory(path=f"{HOME}/.config/opencode", user=USER, group=GROUP, mode="750")
for name in ("AGENTS.md", "opencode.json", "plugins"):
    links[f"{HOME}/.config/opencode/{name}"] = f"../../src/dotfiles/.config/opencode/{name}"
for destination, target in links.items():
    files.link(path=destination, target=target, user=USER, group=GROUP, force=True)

files.put(name="Write local git config", src="experiments/pyinfra-opencode/files/gitconfig.local", dest=f"{HOME}/.gitconfig.local", user=USER, group=GROUP, mode="640")
files.directory(path="/etc/opencode", user="root", group="root", mode="755")

route = json.loads(host.get_fact(Command, command="ip -j -4 route get 1.1.1.1"))
addresses = [item.get("prefsrc") for item in route if item.get("prefsrc")]
if len(addresses) != 1:
    raise RuntimeError(f"expected one primary IPv4 address, got {addresses}")
octets = addresses[0].split(".")
if int(octets[2]) >= 255:
    raise RuntimeError(f"cannot derive sibling subnet from {addresses[0]}")
template_data = dict(TEMPLATE_DATA, opencode_user_uid=host.get_fact(Users)[USER]["uid"], opencode_sibling_proxy_address=f"{octets[0]}.{octets[1]}.{int(octets[2]) + 1}.1")

units = {
    "opencode.service.j2": "opencode.service",
    "deepseek-harness.service.j2": "deepseek-harness.service",
    "dsh-proxy.socket.j2": "dsh-proxy.socket",
    "dsh-proxy.service.j2": "dsh-proxy.service",
}
for source, unit in units.items():
    files.template(name=f"Install {unit}", src=str(TEMPLATES / source), dest=f"/etc/systemd/system/{unit}", user="root", group="root", mode="644", jinja_env_kwargs={"loader": AnsibleIncludeLoader(str(TEMPLATES)), "trim_blocks": True}, **template_data)
for service in ("opencode.service", "deepseek-harness.service", "dsh-proxy.socket"):
    systemd.service(name=f"Enable {service}", service=service, running=True, enabled=True, daemon_reload=True)

# Match the default role behavior when Kimi is disabled.
systemd.service(name="Disable Kimi", service="kimi.service", running=False, enabled=False, _ignore_errors=True)
files.file(name="Remove Kimi unit", path="/etc/systemd/system/kimi.service", present=False)
