from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "roles" / "opencode" / "templates"

PACKAGES = [
    "build-essential", "bubblewrap", "fuse3", "gh", "git", "iproute2",
    "npm", "python-is-python3", "ripgrep", "rustup", "xz-utils", "zstd", "zsh",
]

USER = "opencode"
GROUP = "opencode"
HOME = "/home/opencode"
SRC = f"{HOME}/src"
NODE_VERSION = "24.20.0"
NODE_ARCH = "linux-arm64"
NODE_DIR = f"/opt/node-v{NODE_VERSION}-{NODE_ARCH}"
NODE_BIN = f"{NODE_DIR}/bin"
NODE_ARCHIVE = f"/tmp/node-v{NODE_VERSION}-{NODE_ARCH}.tar.xz"
NODE_URL = f"https://nodejs.org/dist/v{NODE_VERSION}/node-v{NODE_VERSION}-{NODE_ARCH}.tar.xz"
NVIM_DIR = "/opt/nvim-linux-arm64"
NVIM_ARCHIVE = "/tmp/nvim-linux-arm64.tar.gz"
NVIM_URL = "https://github.com/neovim/neovim/releases/latest/download/nvim-linux-arm64.tar.gz"
CODEX_VERSION = "rust-v0.153.4"
CODEX_ARCHIVE = "/tmp/codex-aarch64-unknown-linux-musl.zst"
CODEX_BIN = f"{HOME}/.local/bin/codex"
CODEX_URL = f"https://github.com/openai/codex/releases/download/{CODEX_VERSION}/codex-aarch64-unknown-linux-musl.zst"
DSH_DIR = f"{HOME}/.deepseek-harness"
DSH_PROFILES = f"{HOME}/.dsh/profiles"
DSH_PLUGINS_REPO = f"{SRC}/dsh-plugins"

REPOSITORIES = [
    ("https://github.com/quark-zju/dotfiles", f"{SRC}/dotfiles"),
    ("https://github.com/quark-zju/leash", f"{SRC}/leash"),
]

TEMPLATE_DATA = {
    "opencode_service_name": "opencode",
    "opencode_user": USER,
    "opencode_group": GROUP,
    "opencode_home": HOME,
    "opencode_src_dir": SRC,
    "opencode_node_bin_dir": NODE_BIN,
    "opencode_env_file": "/etc/opencode/opencode.env",
    "opencode_leash_bin": f"{HOME}/.cargo/bin/leash",
    "opencode_bin": "/usr/local/bin/opencode",
    "opencode_log_level": "ERROR",
    "opencode_web_hostname": "0.0.0.0",
    "opencode_web_port": 4096,
    "opencode_restart_sec": "15s",
    "opencode_start_limit_interval_sec": "5min",
    "opencode_start_limit_burst": 5,
    "opencode_memory_high": "650M",
    "opencode_memory_max": "800M",
    "deepseek_harness_service_name": "deepseek-harness",
    "deepseek_harness_dir": DSH_DIR,
    "deepseek_harness_web_hostname": "127.0.0.1",
    "deepseek_harness_web_port": 3080,
    "deepseek_harness_proxy_service_name": "dsh-proxy",
    "deepseek_harness_proxy_bin": "/usr/lib/systemd/systemd-socket-proxyd",
    "deepseek_harness_proxy_bind_address": "0.0.0.0",
    "deepseek_harness_proxy_port": 3088,
    "pnpm_path": SimpleNamespace(stdout="/usr/local/bin/pnpm"),
    "opencode_private_lan_networks": ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "169.254.0.0/16", "fc00::/7", "fe80::/10"],
    "opencode_resolved_addresses": ["127.0.0.53", "127.0.0.54"],
}
