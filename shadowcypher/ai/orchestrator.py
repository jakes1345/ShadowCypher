"""ShadowCypher AI Orchestrator — DeepHat Autonomous Script-Writer Subsystem."""

import requests
import json
import os
from shadowcypher.core.logger import logger

class AIOrchestrator:
    """The 'Brain' of the suite. Orchestrates DeepHat-V1-7B for script generation."""
    def __init__(self, model="DeepHat-V1-7B:latest"):
        self.model = model
        self.base_url = "http://localhost:11434/api/generate"
        self.payload_dir = "payloads"
        os.makedirs(self.payload_dir, exist_ok=True)

    def execute_query(self, query, callback=None):
        """Execute a query and handle autonomous script-writing logic."""
        logger.info("ai", f"DeepHat Query: {query}")
        
        if callback: callback("[TENGU] ACCESSING_LOCAL_OLLAMA_BACKEND...")
        
        prompt = f"ACT AS SHADOWCYPHER DEEPHAT OFFENSIVE AI. QUERY: {query}"
        try:
            if callback: callback(f"[TENGU] SYNCING_MODEL_{self.model}...")
            response = requests.post(self.base_url, json={
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }, timeout=120)  # Extended mission-critical timeout
            
            if callback: callback("[TENGU] DECODING_GENERATED_SIGHTING...")
            
            if response.status_code == 200:
                result = response.json().get("response", "")
                
                # SELF-CORRECTION: Detect if AI generated a script block
                if "```python" in result or "```bash" in result:
                    self._extract_and_write_script(result)
                
                return result
            else:
                return "ERROR: OLLAMA_BACKEND_UNREACHABLE"
        except Exception as e:
            return f"ERROR: SWARM_FAILURE [{str(e)}]"

    def _extract_and_write_script(self, text):
        """Extract code blocks and write them to the payloads directory autonomously."""
        import re
        # Find all triple-backtick blocks
        blocks = re.findall(r"```(python|bash)\n(.*?)\n```", text, re.DOTALL)
        for i, (lang, code) in enumerate(blocks):
            ext = "py" if lang == "python" else "sh"
            filename = f"deephat_gen_{i}.{ext}"
            filepath = os.path.join(self.payload_dir, filename)
            
            with open(filepath, "w") as f:
                f.write(code)
            
            logger.info("ai", f"AUTONOMOUS_SCRIPT_WRITTEN: {filepath}")
            # We add a notice to the AI response (Internal)
            print(f"[TACTICAL] Script saved to {filepath}")
