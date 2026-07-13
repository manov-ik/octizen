"""
network/network_manager.py

NetworkManager for Octizen.
Coordinates scanning, client connections, and AP mode fallback using nmcli.
"""

import subprocess
import shutil
import re
from core.logger import logger
from storage.database_manager import DatabaseManager
from devices.led import LEDManager

HOTSPOT_SSID = "Octizen-Setup"
HOTSPOT_PASSWORD = "octizen123"


class NetworkManager:
    """
    Manages Wi-Fi networking clients and hotspot servers.
    Wraps 'nmcli' shell commands.
    """

    def __init__(self, db_manager: DatabaseManager, event_manager, led_manager: LEDManager):
        self._db = db_manager
        self._event_manager = event_manager
        self._led = led_manager
        self._nmcli_available = shutil.which("nmcli") is not None

        if not self._nmcli_available:
            logger.warning("[Network] nmcli not found in system path. Client/AP modes will be mocked.")

    def scan_networks(self) -> list[dict]:
        """
        Scan available Wi-Fi signals.
        Returns list of dicts: [{"ssid": "MyWiFi", "signal": 85, "security": "WPA2"}]
        """
        if not self._nmcli_available:
            # Mock scan for local development / testing
            return [
                {"ssid": "Mock-Home-WiFi", "signal": 90, "security": "WPA2"},
                {"ssid": "Mock-Office-Net", "signal": 65, "security": "WPA2"},
                {"ssid": "MyHotspot", "signal": 80, "security": "WPA2"},
            ]

        try:
            # Rescan to populate latest list
            subprocess.run(["nmcli", "device", "wifi", "rescan"], capture_output=True, timeout=5)
            
            # List available signals
            # Format: SSID:SIGNAL:SECURITY
            result = subprocess.run(
                ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            
            networks = []
            seen_ssids = set()
            for line in result.stdout.strip().split("\n"):
                if not line or ":" not in line:
                    continue
                
                # Split fields using escaped colons check
                # nmcli -t output escapes ':' as '\:' in SSID names, but splits on unescaped ':'
                parts = re.split(r'(?<!\\):', line)
                if len(parts) >= 3:
                    ssid = parts[0].replace(r"\:", ":").strip()
                    signal_str = parts[1].strip()
                    security = parts[2].strip()
                    
                    if not ssid or ssid in seen_ssids:
                        continue
                    
                    seen_ssids.add(ssid)
                    try:
                        signal = int(signal_str)
                    except ValueError:
                        signal = 0
                        
                    networks.append({
                        "ssid": ssid,
                        "signal": signal,
                        "security": security
                    })
            return sorted(networks, key=lambda x: x["signal"], reverse=True)
            
        except Exception as e:
            logger.error(f"[Network] Scan failed: {e}")
            return []

    def get_active_ssid(self) -> str | None:
        """Get the active Wi-Fi SSID connected to the device, or None."""
        if not self._nmcli_available:
            return None
        try:
            res = subprocess.run(
                ["nmcli", "-t", "-f", "ACTIVE,SSID", "device", "wifi"],
                capture_output=True,
                text=True,
                timeout=5
            )
            for line in res.stdout.strip().split("\n"):
                if line.startswith("yes:"):
                    ssid = line.split(":", 1)[1].strip()
                    if ssid:
                        return ssid
            return None
        except Exception:
            return None

    def get_active_wifi_connection(self) -> str | None:
        """Get the active Wi-Fi connection profile name (e.g. 'Hotspot' or 'netplan-wlan0-H&M')."""
        if not self._nmcli_available:
            return None
        try:
            res = subprocess.run(
                ["nmcli", "-t", "-f", "ACTIVE,NAME,TYPE", "connection", "show"],
                capture_output=True,
                text=True,
                timeout=5
            )
            for line in res.stdout.strip().split("\n"):
                if line.startswith("yes:"):
                    parts = line.split(":")
                    if len(parts) >= 3 and "wireless" in parts[2]:
                        return parts[1].strip()
            return None
        except Exception:
            return None

    def is_already_connected(self) -> bool:
        """
        Check if the Wi-Fi interface is actively connected to a client network.
        Returns False if not connected or if connected to our own setup hotspot.
        """
        active_ssid = self.get_active_ssid()
        return active_ssid is not None and active_ssid != HOTSPOT_SSID

    def check_and_connect(self, force: bool = False) -> bool:
        """
        Checks available networks and connects to the highest priority matching profile.
        If force=False and we are already connected to client Wi-Fi, skips check to save SSH.
        If force=True (button hold) or not connected, scans and loops through all matching networks.
        
        Returns:
            True if connected to client Wi-Fi, False if fallback AP triggered.
        """
        logger.info("[Network] Initiating network configuration check...")
        
        # Safety Check: If already online, don't interrupt active SSH sessions unless forced!
        if not force:
            active_ssid = self.get_active_ssid()
            if active_ssid is not None and active_ssid != HOTSPOT_SSID:
                logger.info(f"[Network] Already connected to client Wi-Fi: {active_ssid}. Skipping boot config changes.")
                self._led.on()
                self._event_manager.emit("network.connected", {"ssid": active_ssid})
                return True

        self._led.blink(on_time=0.2, off_time=0.2)  # fast blink = searching

        # If the fallback hotspot is running, we MUST stop it first so the single Wi-Fi radio
        # is free to scan for client Wi-Fi signals in the air.
        if self._nmcli_available:
            try:
                active_ssid = self.get_active_ssid()
                if active_ssid == HOTSPOT_SSID:
                    active_conn = self.get_active_wifi_connection()
                    if active_conn:
                        logger.info(f"[Network] Disabling active setup hotspot connection '{active_conn}' to scan for client networks...")
                        subprocess.run(["nmcli", "connection", "down", active_conn], capture_output=True, timeout=10)
                        # Also attempt to turn down HOTSPOT_SSID directly as fallback
                        subprocess.run(["nmcli", "connection", "down", HOTSPOT_SSID], capture_output=True, timeout=10)
                        import time
                        time.sleep(1.5)  # Let hardware settle
            except Exception as e:
                logger.error(f"[Network] Error turning down hotspot for scan: {e}")

        # 1. Fetch saved networks from DB
        saved_networks = self._db.get_wifi_networks()
        if not saved_networks:
            logger.warning("[Network] No saved Wi-Fi networks found in database.")
            self._start_ap_mode()
            return False

        # 2. Scan available airwaves
        visible_networks = {net["ssid"] for net in self.scan_networks()}
        
        # 3. Match saved vs visible (returns a list of matched networks sorted by priority)
        matching_networks = [saved for saved in saved_networks if saved["ssid"] in visible_networks]

        if not matching_networks:
            logger.warning("[Network] None of the saved Wi-Fi networks are in range.")
            self._start_ap_mode()
            return False

        # 4. Attempt connection in priority order (ASC)
        # If the highest priority connection fails, try the next matches as fallback!
        connected = False
        for net in matching_networks:
            ssid = net["ssid"]
            password = net["password"]
            
            logger.info(f"[Network] Attempting connection to: {ssid}...")
            if self._connect_to_wifi(ssid, password):
                logger.info(f"[Network] Successfully connected to client Wi-Fi: {ssid} 🎉")
                self._led.on()  # steady ON = connected
                self._event_manager.emit("network.connected", {"ssid": ssid})
                connected = True
                break
            else:
                logger.error(f"[Network] Connection failed to SSID: {ssid}. Trying other visible matches...")

        if not connected:
            self._start_ap_mode()
            return False
        return True

    def _connect_to_wifi(self, ssid: str, password: str) -> bool:
        """Runs the connection command."""
        # If we are already connected to this network, don't run nmcli (which returns error code for active connection)
        if self.get_active_ssid() == ssid:
            logger.info(f"[Network] Device is already connected to {ssid}. Skipping redundant connect command.")
            return True

        if not self._nmcli_available:
            time.sleep(2)  # Mock delay
            return ssid != "Mock-Fail-WiFi"

        try:
            # Disconnect any active hotspot first using connection down on Hotspot
            subprocess.run(["nmcli", "connection", "down", "Hotspot"], capture_output=True)
            
            # Connect to client network
            res = subprocess.run(
                ["nmcli", "device", "wifi", "connect", ssid, "password", password],
                capture_output=True,
                text=True,
                timeout=20,
            )
            if res.returncode != 0:
                logger.error(f"[Network] nmcli failed to connect to {ssid}. Exit code: {res.returncode}\nstdout: {res.stdout.strip()}\nstderr: {res.stderr.strip()}")
            return res.returncode == 0
        except Exception as e:
            logger.error(f"[Network] Client connection execution failed: {e}")
            return False

    def _start_ap_mode(self) -> None:
        """Fallback to local Access Point hotspot server (Bypassed in dev mode for SSH safety)."""
        logger.info("[Network] Fallback AP hotspot mode is bypassed to prevent SSH disconnects.")
        self._led.blink(on_time=0.5, off_time=0.5)  # normal blink = disconnected, no AP active
        self._event_manager.emit("network.ap_started", {"ssid": "Bypassed (Dev Mode)"})
