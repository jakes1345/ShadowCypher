from flask import Flask, request, render_template_string, send_file, abort
import os
import sqlite3
import subprocess

app = Flask(__name__)

# Database Setup
def init_db():
    conn = sqlite3.connect('lab.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER, username TEXT, password TEXT)')
    c.execute('INSERT OR IGNORE INTO users VALUES (1, "admin", "P@ssw0rd123")')
    c.execute('INSERT OR IGNORE INTO users VALUES (2, "operator", "ShadowOperative")')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template_string('''
        <style>
            body { background: #0a0a0a; color: #00f2ff; font-family: monospace; padding: 50px; }
            h1 { border-bottom: 2px solid #00f2ff; padding-bottom: 10px; }
            .nav { margin-bottom: 30px; }
            a { color: #00f2ff; margin-right: 20px; text-decoration: none; border: 1px solid #00f2ff; padding: 5px 15px; }
            .log { background: #111; padding: 20px; border: 1px solid #333; height: 300px; overflow: auto; }
        </style>
        <h1>CITADEL // TRAINING_RANGE_v1.0</h1>
        <div class="nav">
            <a href="/ping">NETWORK_DIAGNOSTIC</a>
            <a href="/download">FILE_ARCHIVE</a>
            <a href="/admin">RESTRICTED_ACCESS</a>
        </div>
        <p>SYSTEM_STATUS: OPERATIONAL</p>
        <div class="log">
            [SYS] BOOT_SEQUENCE_COMPLETE<br>
            [SYS] TRAINING_MODE: ENABLED<br>
            [SYS] WAITING_FOR_OPERATOR...
        </div>
    ''')

@app.route('/ping')
def ping():
    ip = request.args.get('ip', '127.0.0.1')
    # COMMAND INJECTION VULNERABILITY
    if ip:
        try:
            # Dangerous: shell=True with user input
            output = subprocess.check_output(f"ping -c 1 {ip}", shell=True, stderr=subprocess.STDOUT, timeout=5).decode()
        except Exception as e:
            output = str(e)
    else:
        output = "Enter IP to ping"
    
    return render_template_string(f'''
        <h2>NETWORK_DIAGNOSTIC</h2>
        <form>
            IP: <input type="text" name="ip" value="{ip}">
            <input type="submit" value="PING">
        </form>
        <pre style="background: #000; padding: 20px;">{output}</pre>
        <a href="/">BACK</a>
    ''')

@app.route('/download')
def download():
    filename = request.args.get('file', 'info.txt')
    # PATH TRAVERSAL VULNERABILITY
    # Vulnerable to ../../../etc/passwd
    path = os.path.join(os.getcwd(), 'static', filename)
    try:
        return send_file(path)
    except Exception as e:
        return f"Error: {e}"

@app.route('/admin')
def admin():
    # 403 BYPASS VULNERABILITY
    # Checks for X-Forwarded-For or X-Custom-IP-Authorization
    client_ip = request.remote_addr
    forwarded_for = request.headers.get('X-Forwarded-For')
    custom_ip = request.headers.get('X-Custom-IP-Authorization')
    
    if forwarded_for == '127.0.0.1' or custom_ip == '127.0.0.1':
        return "<h1>WELCOME ADMIN</h1><p>FLAG{BYPASS_SUCCESSFUL_GHOST_PROTOCOL}</p>"
    
    abort(403)

@app.errorhandler(403)
def forbidden(e):
    return "<h1>403 FORBIDDEN</h1><p>Access Restricted to Internal Operators Only.</p>", 403

if __name__ == '__main__':
    # Running on 5000 to avoid conflict with potential C2 listeners
    app.run(host='0.0.0.0', port=5000, debug=True)
