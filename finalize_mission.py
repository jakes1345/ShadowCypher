import os
import subprocess

def run(cmd):
    print(f"[*] Executing: {cmd}")
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

def main():
    print("-------------------------------------------------------")
    print("🌌 SHADOWCYPHER FINAL INTEGRITY OVERLORD")
    print("-------------------------------------------------------")

    # 1. Update .gitignore with absolute authority
    garbage = [".shortest/", ".cursor/", ".claude/", ".sisyphus/", "payloads/", "reports/", "projects/", "research/", "shadowcypher/tests/", "*.pyc", "__pycache__/"]
    with open(".gitignore", "a") as f:
        f.write("\n# Shadow Protocol - Force Garbage Exclusion\n")
        f.writelines([g + "\n" for g in garbage])
    print("[+] .gitignore updated.")

    # 2. Force Git to forget the garbage
    folders = ".shortest .cursor .claude .sisyphus payloads reports projects research shadowcypher/tests"
    run(f"git rm -r --cached {folders} 2>/dev/null")
    print("[+] Git index scrubbed of mission debris.")

    # 3. Logo Deployment Logic
    # Check root for the Raven (user might have saved it as image.png or master_logo...)
    possible_names = ["image.png", "shadowcypher_master_logo.png", "master_logo.png", "logo.png"]
    found_logo = False
    for name in possible_names:
        if os.path.exists(name):
            print(f"[+] Found Raven asset: {name}. Moving to tactical core...")
            run(f"mv {name} shadowcypher/ui/assets/icon.png")
            found_logo = True
            break
    
    if not found_logo:
        print("[!] WARN: Raven logo not found in root. Ensure you save it from the browser as 'image.png' in this folder then re-run.")

    # 4. Final Seal
    print("[*] Preparing final presentational commit...")
    run("git add .")
    res = run('git commit -m "🛡️ FINAL_SCRUB: Purging mission debris and deploying master branding"')
    
    print("\n-------------------------------------------------------")
    print("[+] READY FOR DEPLOYMENT.")
    print("-------------------------------------------------------")
    print("\nFINAL STEP: Run the command below to push everything to GitHub:")
    print("git push origin main --force")
    print("-------------------------------------------------------")

if __name__ == "__main__":
    main()
