"""
OpenControl Integration Module — Tactical Infrastructure Gateway.
Bridges ShadowCypher to the OpenControl (AnomalyCo) control plane
for remote hardware and node orchestration.
"""

import json
import requests
import uuid
from typing import Dict, List, Any, Optional
from shadowcypher.core.module import BaseModule
from shadowcypher.core.logger import logger
from shadowcypher.core.config import config
try:
    from ai_engine.autoagent.registry import register_tool
except ImportError:
    def register_tool(fn): return fn

class OpenControlClient:
    """Client for the OpenControl Infrastructure Gateway."""
    def __init__(self, endpoint: str = None, api_key: str = None):
        self.endpoint = endpoint or config.get("opencontrol", "endpoint", default="http://127.0.0.1:9090")
        api_key = api_key or config.get("opencontrol", "api_key", default="")
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    def list_nodes(self) -> List[Dict[str, Any]]:
        """Fetch all registered tactical nodes from OpenControl."""
        try:
            res = requests.get(f"{self.endpoint}/api/v1/nodes", headers=self.headers, timeout=10)
            return res.json().get("nodes", [])
        except Exception as e:
            logger.error("opencontrol", f"NODE_FETCH_FAILURE: {e}")
            return []

    def execute_remote(self, node_id: str, command: str) -> Dict[str, Any]:
        """Sends a high-velocity command to a remote infrastructure node."""
        payload = {"command": command, "node_id": node_id, "timestamp": uuid.uuid4().hex}
        try:
            res = requests.post(f"{self.endpoint}/api/v1/execute", 
                               json=payload, headers=self.headers, timeout=30)
            return res.json()
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}

# --- AUTOAGENT TOOLS ---

@register_tool(name="oc_list_infrastructure")
def oc_list_infrastructure() -> str:
    """
    Returns a list of all remote hardware nodes managed by the OpenControl gateway.
    Use this to identify targets for remote orchestration.
    """
    client = OpenControlClient()
    nodes = client.list_nodes()
    if not nodes:
        return "No nodes detected in the OpenControl gateway."
    
    output = "OPENCONTROL_TOPOLOGY:\n"
    for n in nodes:
        output += f"- NODE_ID: {n.get('id')} | IP: {n.get('ip')} | STATUS: {n.get('status')}\n"
    return output

@register_tool(name="oc_strike_remote")
def oc_strike_remote(node_id: str, command: str) -> str:
    """
    Executes a shell command on a remote infrastructure node via OpenControl.
    
    Args:
        node_id: The unique ID of the target node.
        command: The shell command to execute (e.g., 'cat /etc/shadow' or 'reboot').
    """
    client = OpenControlClient()
    res = client.execute_remote(node_id, command)
    
    if res.get("status") == "SUCCESS":
        return f"STRIKE_SUCCESS [{node_id}]:\n{res.get('output', 'No Output.')}"
    return f"STRIKE_FAILED [{node_id}]: {res.get('error', 'Unknown Error')}"

class OpenControlModule(BaseModule):
    """ShadowCypher Module Wrapper for OpenControl."""
    def __init__(self):
        super().__init__(module_name="opencontrol")
        self.client = OpenControlClient()

    def run(self, **kwargs):
        """Delegate to the underlying OpenControlClient instead of silently no-op'ing."""
        action = kwargs.get("action")
        if not action:
            return {"status": "error", "message": "opencontrol.run: missing 'action' kwarg"}
        fn = getattr(self.client, action, None)
        if not callable(fn):
            return {"status": "error", "message": f"opencontrol.run: unknown action '{action}'"}
        try:
            return {"status": "ok", "result": fn(**{k: v for k, v in kwargs.items() if k != "action"})}
        except Exception as e:
            return {"status": "error", "message": str(e)}

# Legacy export for existing scripts
oc_module = OpenControlModule()
