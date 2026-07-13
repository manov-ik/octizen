"""
api/routes/wifi.py

Endpoints for scanning available Wi-Fi signals and managing credentials.
"""

from fastapi import APIRouter, Request, HTTPException
from api.schemas import WifiSave

router = APIRouter(prefix="/wifi", tags=["Wi-Fi"])


@router.get("/scan")
def scan_wifi(request: Request):
    network_mgr = request.app.state.network
    return network_mgr.scan_networks()


@router.get("/saved")
def get_saved_wifi(request: Request):
    db = request.app.state.db
    return db.get_wifi_networks()


@router.post("/saved")
def save_wifi(request: Request, credential: WifiSave):
    db = request.app.state.db
    db.save_wifi_network(credential.ssid, credential.password, credential.priority)
    return {"ssid": credential.ssid, "status": "saved"}


@router.delete("/saved/{ssid}")
def delete_wifi(request: Request, ssid: str):
    db = request.app.state.db
    
    # Check if network exists before deleting
    saved = db.get_wifi_networks()
    if not any(net["ssid"] == ssid for net in saved):
        raise HTTPException(status_code=404, detail="Wi-Fi network credential not found")
        
    db.delete_wifi_network(ssid)
    return {"ssid": ssid, "status": "deleted"}
