import numpy as np
import threading
import time
from typing import List, Dict, Any, Optional
from scipy.ndimage import gaussian_laplace

from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus

class ShadowPulse:
    """
    The mathematical 'Sixth Sense' of ShadowCypher.
    Analyzes high-noise temporal signals using Scale-Space Analysis (DSP core of WST).
    Designed for detecting non-stationary transients and hardware artifacts.
    """

    def __init__(self):
        self._active = False
        self._samples: Dict[str, np.ndarray] = {}
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
                self._samples[stream_id] = np.zeros(self._max_history)
            
            # Shift existing data and append new value
            samples_array = self._samples[stream_id]
            samples_array[:-1] = samples_array[1:]
            samples_array[-1] = value

    def analyze_spectrum(self, stream_id: str) -> Dict[str, Any]:
        """
        Performs Scale-Space Analysis (Approximation of WST) on the requested stream.
        Detects translation-invariant transients by analyzing feature energy across scales.
        """
        with self._lock:
            data = self._samples.get(stream_id)
            if data is None or np.sum(np.abs(data)) == 0:
                return {"status": "INSUFFICIENT_DATA"}

        # --- DSP CORE: Scale-Space Analysis using Gaussian Derivatives ---
        
        # 1. Define Scales (Sigma)
        # We analyze features across multiple scales (sigma) to capture multi-resolution information.
        # Ensure we have enough data points for a valid logspace
        num_scales = max(4, int(np.ceil(np.log2(len(data)))))
        sigmas = np.logspace(np.log10(0.5), np.log10(10.0), num=num_scales)
        
        scale_energies = []
        
        # 2. Calculate Scale-Space Coefficients
        for sigma in sigmas:
            # Apply Gaussian Laplacian to capture local curvature/transients
            laplacian_filtered = gaussian_laplace(data, sigma=sigma)
            
            # The energy at this scale is the L2 norm of the filtered signal
            energy = np.linalg.norm(laplacian_filtered)
            scale_energies.append(energy)

        scale_energies = np.array(scale_energies)
        
        # 3. Anomaly Scoring (Non-Stationarity Metric)
        mean_energy = np.mean(scale_energies)
        max_energy = np.max(scale_energies)
        
        # Score calculation: High ratio indicates non-stationarity/transient event.
        score = (max_energy / (mean_energy + 1e-9))
        
        self.last_anomaly_score = score
        # Threshold calibrated for high-fidelity detection
        is_safe = score < 2.8 
        
        if not is_safe and self.is_nominal:
            self.is_nominal = False
            self.throttle_active = True
            self._broadcast_anomaly(stream_id, score)
        elif is_safe and not self.is_nominal:
            self.is_nominal = True
            self.throttle_active = False

        return {
            "stream": stream_id,
            "s_scale_mean_energy": round(float(mean_energy), 4),
            "s_max_scale_energy": round(float(max_energy), 4),
            "s_anomaly_score": round(float(score), 4),
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

    def reset(self, stream_id: Optional[str] = None):
        """Flush the spectrum buffers."""
        with self._lock:
            if stream_id:
                self._samples[stream_id] = np.zeros(self._max_history)
            else:
                self._samples = {}
        logger.info("pulse", "SPECTRUM_BUFFERS_FLUSHED")

# Global Singleton Engine
pulse = ShadowPulse()
