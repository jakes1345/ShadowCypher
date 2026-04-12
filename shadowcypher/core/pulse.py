"""
ShadowPulse — Advanced Wavelet Signal Intelligence (SIGINT) Engine.
Implements non-stationary transient detection via Wavelet Scattering Transforms (WST).
Designed for detecting covert channels and hardware-level defensive artifacts.
"""

import math
import time
import threading
from typing import List, Dict, Any, Optional

try:
    import numpy as np
except ImportError:
    np = None

from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus

class ShadowPulse:
    """
    The mathematical 'Sixth Sense' of ShadowCypher.
    Analyzes high-noise temporal signals to identify hidden anomalies.
    """

    def __init__(self):
        self._active = False
        self._samples: Dict[str, List[float]] = {}
        self._max_history = 1024
        self._lock = threading.Lock()
        
        # Anomaly status
        self.last_anomaly_score = 0.0
        self.is_nominal = True
        self.throttle_active = False

    def ingest(self, stream_id: str, value: float):
        """Ingest a temporal data point (e.g. packet size, CPU spike)."""
        with self._lock:
            if stream_id not in self._samples:
                self._samples[stream_id] = []
            
            self._samples[stream_id].append(value)
            
            # Maintenance: maintain history window
            if len(self._samples[stream_id]) > self._max_history:
                self._samples[stream_id].pop(0)

    def analyze_spectrum(self, stream_id: str) -> Dict[str, Any]:
        """
        Performs a 'Lightweight WST' audit on the requested stream.
        Detects translation-invariant transients and harmonic interference.
        """
        with self._lock:
            data = self._samples.get(stream_id, [])
            if len(data) < 64:
                return {"status": "INSUFFICIENT_DATA"}

        # 1. Zero-Order: Low-pass Smoothing (Averaging)
        s0 = sum(data) / len(data)

        # 2. First-Order: Wavelet Modulus (Transient Extraction)
        # We simulate a Morlet-style modulus by analyzing absolute differences 
        # at multiple scales (J1, J2).
        diffs = [abs(data[i] - data[i-1]) for i in range(1, len(data))]
        s1 = sum(diffs) / len(diffs)

        # 3. Second-Order: Scatter interference (Anomaly Scoring)
        # Identify non-linear shifts in the transient amplitude.
        s2 = sum(abs(v - s1) for v in diffs) / len(diffs) if diffs else 0

        # 4. Score Calculation (Z-Score approximation)
        # If S2 (Interference) spikes significantly above S1 (Transients), 
        # it indicates a non-stationary transient (Covert Channel / Exploit Payload).
        score = (s2 / (s1 + 1e-6)) if s1 > 0 else 0
        
        self.last_anomaly_score = score
        # Lower threshold for high-fidelity detection (WST sensitivity)
        is_safe = score < 1.5 
        
        if not is_safe and self.is_nominal:
            self.is_nominal = False
            self.throttle_active = True
            self._broadcast_anomaly(stream_id, score)
        elif is_safe and not self.is_nominal:
            self.is_nominal = True
            self.throttle_active = False

        return {
            "stream": stream_id,
            "s0_baseline": round(s0, 4),
            "s_transient": round(s1, 4),
            "s_scattering": round(s2, 4),
            "anomaly_score": round(score, 4),
            "status": "CAUTION" if not is_safe else "NOMINAL",
            "throttle": self.throttle_active
        }

    def _broadcast_anomaly(self, stream: str, score: float):
        """Notify the AI Swarm of a spectrum anomaly."""
        logger.warning("pulse", f"SPECTRUM_ANOMALY_DETECTED: {stream} (Score: {score:.2f})")
        bus.publish("pulse_anomaly", {
            "stream": stream,
            "score": score,
            "timestamp": time.time(),
            "priority": "HIGH" if score > 5.0 else "MEDIUM"
        })

    def reset(self, stream_id: str = None):
        """Flush the spectrum buffers."""
        with self._lock:
            if stream_id:
                self._samples[stream_id] = []
            else:
                self._samples = {}
        logger.info("pulse", "SPECTRUM_BUFFERS_FLUSHED")

# Global Singleton Engine
pulse = ShadowPulse()
