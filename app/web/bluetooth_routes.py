"""Read-only Bluetooth discovery UI.

Scanning runs on the MeshWX server host, not in the browser. No pairing,
radio connection, or transmission is performed here.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..bluetooth_discovery import discover_bluetooth_devices

router = APIRouter()


@router.get("/settings/bluetooth", response_class=HTMLResponse)
async def bluetooth_page(request: Request):
    from .routes import render
    return render(request, "bluetooth.html")


@router.post("/settings/bluetooth/scan")
async def bluetooth_scan():
    from fastapi import HTTPException
    try:
        devices = await discover_bluetooth_devices()
    except (RuntimeError, OSError, TimeoutError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"devices": [
        {"name": d.name, "address": d.address, "rssi": d.rssi}
        for d in devices
    ]}


@router.get("/api/radios/status")
async def radio_status(request: Request):
    """Read-only transport diagnostics for a dashboard or support checks."""
    tx = request.app.state.tx
    return {"radios": tx.status(), "queue_depth": tx.queue_depth,
            "any_connected": tx.connected,
            "connection_history": tx.connection_history()}


@router.get("/api/radios/discover-network")
async def network_radio_discovery():
    """Best-effort local mDNS discovery of Meshtastic TCP devices."""
    from fastapi import HTTPException
    from ..network_discovery import discover_network_radios
    try:
        radios = await discover_network_radios()
    except (RuntimeError, OSError, TimeoutError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"radios": radios}
