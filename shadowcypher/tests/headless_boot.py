"""
ShadowCypher Headless Core — Minimal bootstrapper for Bot/Hub testing.
Bypasses GTK UI for backend integrity validation.
"""

import time
def main():
    print("[\u26a1] HEADLESS_BOOT: INITIALIZING_TACTICAL_BACKEND")
    
    # Importing hub triggers __init__ -> sentinel.start()
    from shadowcypher.core.hub import hub
    
    print("[RUN] System online. Monitoring IRC bridge...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[EXIT] Shutting down.")

if __name__ == "__main__":
    main()
