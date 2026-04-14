"""
Cluster-related tools for Proxmox MCP.

This module provides tools for monitoring and managing Proxmox clusters:
- Retrieving overall cluster health status
- Monitoring quorum status and node count
- Tracking cluster resources and configuration
- Checking cluster-wide service availability

The tools provide essential information for maintaining
cluster health and ensuring proper operation.
"""
import time
from typing import List, Optional
from mcp.types import TextContent as Content
from proxmox_mcp.tools.base import ProxmoxTool

class ClusterTools(ProxmoxTool):
    """Tools for managing Proxmox cluster.
    
    Provides functionality for:
    - Monitoring cluster health and status
    - Tracking quorum and node membership
    - Managing cluster-wide resources
    - Verifying cluster configuration
    
    Essential for maintaining cluster health and ensuring
    proper operation of the Proxmox environment.
    """

    def get_cluster_status(self) -> List[Content]:
        """Get overall Proxmox cluster health and configuration status.

        Retrieves comprehensive cluster information including:
        - Cluster name and identity
        - Quorum status (essential for cluster operations)
        - Active node count and health
        - Resource distribution and status
        
        This information is critical for:
        - Ensuring cluster stability
        - Monitoring node membership
        - Verifying resource availability
        - Detecting potential issues

        Returns:
            List of Content objects containing formatted cluster status:
            {
                "name": "cluster-name",
                "quorum": true/false,
                "nodes": count,
                "resources": [
                    {
                        "type": "resource-type",
                        "status": "status"
                    }
                ]
            }

        Raises:
            RuntimeError: If cluster status query fails due to:
                        - Network connectivity issues
                        - Authentication problems
                        - API endpoint failures
        """
        cached = self._cache_get("cluster:status")
        if cached is not None:
            return self._format_response(cached, "cluster")

        try:
            result = self._call_with_retry(
                "get cluster status", lambda: self.proxmox.cluster.status.get()
            )
        
            first_item = result[0] if result and len(result) > 0 else {}
            status = {
                "name": first_item.get("name") if first_item else None,
                "quorum": first_item.get("quorate") if first_item else None,
                "nodes": len([node for node in result if node.get("type") == "node"]) if result else 0,
                "resources": [res for res in result if res.get("type") == "resource"] if result else []
            }
            self._cache_set("cluster:status", status, ttl_seconds=5)
            return self._format_response(status, "cluster")
        except Exception as e:
            self._handle_error("get cluster status", e)

    def list_tasks(
        self,
        node: Optional[str] = None,
        limit: int = 20,
        errors_only: bool = False,
        running_only: bool = False,
    ) -> List[Content]:
        """List recent Proxmox tasks across the cluster or a single node.

        A task is any Proxmox background operation (backup, clone, start/stop,
        migration, etc.). Each task has a UPID you can pass to get_task_log.
        """
        try:
            if node:
                tasks = self.proxmox.nodes(node).tasks.get(limit=limit)
            else:
                tasks = self.proxmox.cluster.tasks.get()

            if errors_only:
                tasks = [t for t in tasks if t.get("status") and t.get("status") != "OK"]
            if running_only:
                tasks = [t for t in tasks if not t.get("endtime")]

            tasks = tasks[:limit]

            if not tasks:
                return [Content(type="text", text="📋 No tasks matching filter")]

            lines = [f"📋 Proxmox Tasks ({len(tasks)})\n"]
            for t in tasks:
                upid = t.get("upid", "?")
                ttype = t.get("type", "?")
                tnode = t.get("node", "?")
                user = t.get("user", "?")
                start = t.get("starttime")
                end = t.get("endtime")
                status = t.get("status") or ("running" if not end else "OK")

                start_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start)) if start else "?"
                duration = ""
                if start and end:
                    duration = f" ({end - start}s)"
                elif start and not end:
                    duration = " (running)"

                emoji = "🟢" if status == "OK" else ("🟡" if not end else "🔴")
                lines.append(
                    f"{emoji} [{ttype}] {tnode} by {user} @ {start_str}{duration}\n"
                    f"   status: {status}\n"
                    f"   upid:   {upid}"
                )
            return [Content(type="text", text="\n\n".join(lines))]
        except Exception as e:
            self._handle_error("list tasks", e)

    def get_task_log(
        self,
        node: str,
        upid: str,
        limit: int = 200,
    ) -> List[Content]:
        """Fetch the log output of a specific Proxmox task.

        Use upid from list_tasks. Log is truncated to `limit` lines.
        """
        try:
            log_lines = self.proxmox.nodes(node).tasks(upid).log.get(limit=limit)
            status = self.proxmox.nodes(node).tasks(upid).status.get()

            out = [f"📜 Task {upid}"]
            out.append(f"  status: {status.get('status', '?')} | exitstatus: {status.get('exitstatus', '-')}")
            out.append("")
            if isinstance(log_lines, list):
                for entry in log_lines:
                    text = entry.get("t") if isinstance(entry, dict) else str(entry)
                    if text:
                        out.append(text)
            else:
                out.append(str(log_lines))
            return [Content(type="text", text="\n".join(out))]
        except Exception as e:
            if "does not exist" in str(e).lower() or "not found" in str(e).lower():
                raise ValueError(f"Task {upid} not found on node {node}")
            self._handle_error(f"get task log {upid}", e)
