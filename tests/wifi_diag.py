"""
tests/wifi_diag.py

Diagnostics tool for nmcli on Raspberry Pi.
Helps identify parsing or scanning issues.
"""

import subprocess
import shutil

print("=" * 60)
print("  Wi-Fi Diagnostics Tool")
print("=" * 60)

# 1. Check nmcli path
nmcli_path = shutil.which("nmcli")
print(f"nmcli path: {nmcli_path}")
if not nmcli_path:
    print("❌ nmcli is not installed or not in PATH!")
    sys.exit(1)

# 2. Check wifi device state
print("\n--- Device Status (nmcli device) ---")
res = subprocess.run(["nmcli", "device"], capture_output=True, text=True)
print(res.stdout)

# 3. Try scanning
print("\n--- Triggering Rescan (nmcli device wifi rescan) ---")
res = subprocess.run(["nmcli", "device", "wifi", "rescan"], capture_output=True, text=True)
print(f"Exit code: {res.returncode}")
if res.stderr:
    print(f"Stderr: {res.stderr.strip()}")

# 4. Get raw list
print("\n--- Raw Wifi List (nmcli -t -f SSID,SIGNAL,SECURITY device wifi list) ---")
res = subprocess.run(
    ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list"],
    capture_output=True,
    text=True
)
print(f"Exit code: {res.returncode}")
if res.stdout:
    print(res.stdout)
else:
    print("(No output returned)")
if res.stderr:
    print(f"Stderr: {res.stderr.strip()}")

# 5. Check active connection
print("\n--- Active Wi-Fi Connection (nmcli -t -f ACTIVE,SSID device wifi) ---")
res = subprocess.run(
    ["nmcli", "-t", "-f", "ACTIVE,SSID", "device", "wifi"],
    capture_output=True,
    text=True
)
print(res.stdout)
print("=" * 60)
