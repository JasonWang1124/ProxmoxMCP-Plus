# ProxmoxMCP-Plus

Streamable-HTTP MCP server for Proxmox VE — drop-in tool layer for Claude Code, Claude Desktop, or any MCP-compatible client.

This fork trims the upstream [RekklesNA/ProxmoxMCP-Plus](https://github.com/RekklesNA/ProxmoxMCP-Plus) down to a single, long-running HTTP MCP server. The mcpo REST bridge and ISO/template tooling have been removed; the command policy gate, SSH-based container exec, and backup/snapshot tooling are kept. A minimal Docker setup ships for always-on deployment.

Upstream chain: [canvrno/ProxmoxMCP](https://github.com/canvrno/ProxmoxMCP) → [RekklesNA/ProxmoxMCP-Plus](https://github.com/RekklesNA/ProxmoxMCP-Plus) → this fork.

## What's in the box

31 MCP tools across:

| Area | Tools |
| --- | --- |
| Nodes | `get_nodes`, `get_node_status` |
| VMs | `get_vms`, `create_vm`, `execute_vm_command`, `start_vm`, `stop_vm`, `shutdown_vm`, `reset_vm`, `delete_vm` |
| Containers (LXC) | `get_containers`, `create_container`, `start_container`, `stop_container`, `restart_container`, `update_container_resources`, `delete_container`, `get_container_config`, `get_container_ip` |
| Container exec (optional, requires SSH config) | `execute_container_command`, `update_container_ssh_keys` |
| Snapshots | `list_snapshots`, `create_snapshot`, `delete_snapshot`, `rollback_snapshot` |
| Backups | `list_backups`, `create_backup`, `restore_backup`, `delete_backup` |
| Storage / Cluster | `get_storage`, `get_cluster_status` |

Deliberately not included: ISO downloads (use the Proxmox UI) and the OpenAPI/REST bridge. Add them back from upstream if you need them.

## Quick start

```bash
git clone git@github.com:JasonWang1124/ProxmoxMCP-Plus.git
cd ProxmoxMCP-Plus
uv venv
uv pip install -e .
```

Create a config file:

```bash
cp proxmox-config/config.example.json proxmox-config/config.json
$EDITOR proxmox-config/config.json
```

Minimum fields to fill in:

- `proxmox.host` — Proxmox node address
- `auth.user` — e.g. `claude@pve`
- `auth.token_name`, `auth.token_value` — API token for that user

The default transport is **Streamable HTTP** on port `8812`. Pick one of:

**Docker (recommended — always on):**

```bash
docker compose up -d --build
docker compose logs -f proxmox-mcp
```

The container binds to `127.0.0.1:8812` on the host and mounts `proxmox-config/` read-only. `restart: unless-stopped` keeps it running after reboots.

**Bare metal:**

```bash
PROXMOX_MCP_CONFIG=$(pwd)/proxmox-config/config.json python main.py
```

Health check (post `initialize` first — Streamable HTTP needs a session):

```bash
curl -sv -X POST -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"curl","version":"1.0"}}}' \
  http://127.0.0.1:8812/mcp
```

## Connect it to Claude Code / Desktop

Add this to your MCP client config (`~/.claude.json` for Claude Code, or Claude Desktop settings):

```json
{
  "mcpServers": {
    "proxmox": {
      "type": "http",
      "url": "http://127.0.0.1:8812/mcp"
    }
  }
}
```

Restart the client and the Proxmox tools should show up.

## Proxmox API token

Create a dedicated user + token for the MCP server. Never point it at `root@pam` in production.

```bash
# On the Proxmox node
pveum user add claude@pve --comment "Claude MCP"
pveum aclmod / -user claude@pve -role PVEVMAdmin
pveum user token add claude@pve mcp --privsep 0
```

Paste the generated token value into `auth.token_value`. For stricter setups, create a custom role with only the permissions you want and assign it instead of `PVEVMAdmin`.

## Security posture

- **Command policy gate** — `execute_vm_command` and `execute_container_command` are gated by `command_policy.mode` (`deny_all` / `allowlist` / `audit_only`). The example config ships with `audit_only` for dev; switch to `allowlist` before opening this up to shared environments.
- **SSH exec is opt-in** — container command execution tools only register when the `ssh` config section is present. Strict host key checking is on by default.
- **`dev_mode`** only relaxes TLS verification; it does not disable other controls.
- **TLS** — set `proxmox.verify_ssl=true` and keep `security.dev_mode=false` for anything non-local.

## Transports

The upstream supports three MCP transports. This fork defaults to and is tested with **Streamable HTTP**, but STDIO and SSE still work if you set `mcp.transport` accordingly.

| Transport | When to use | `mcp.transport` |
| --- | --- | --- |
| Streamable HTTP | Long-running server, HTTP MCP clients (default) | `STREAMABLE` |
| STDIO | Spawn-per-session, no network exposure | `STDIO` |
| SSE | Legacy MCP clients that don't speak streamable HTTP yet | `SSE` |

## Development

```bash
uv pip install -e ".[dev]"
pytest
ruff check .
mypy src
```

## License

MIT — inherited from upstream. See [LICENSE](LICENSE).
