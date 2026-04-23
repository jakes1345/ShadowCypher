import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
import os, sys, time, subprocess

# Force display 101
os.environ["DISPLAY"] = ":101"
os.environ["PYTHONPATH"] = "."

def capture():
    time.sleep(15) # Wait for app to load
    print("Capturing screenshot...")
    subprocess.run(["scrot", "dashboard_capture.png"])
    print("Done. Killing app.")
    Gtk.main_quit()
    sys.exit(0)

if __name__ == "__main__":
    # Start Xvfb in background
    xvfb = subprocess.Popen(["Xvfb", ":101", "-screen", "0", "1280x720x24"])
    time.sleep(2)
    
    # Start app in background
    app = subprocess.Popen(["python3", "shadowcypher/app.py"])
    
    # Start capture thread
    import threading
    threading.Thread(target=capture, daemon=True).start()
    
    time.sleep(30)
    xvfb.terminate()
    app.terminate()
