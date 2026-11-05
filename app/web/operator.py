"""Operator-facing read-only UX data and safe local preferences."""
from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime, timezone

router = APIRouter()

class Preferences(BaseModel):
    compact: bool = False
    advanced: bool = False
    monitor: bool = False
    show_radios: bool = True
    show_activity: bool = True
    show_weather: bool = True
    show_map: bool = True


class Preview(BaseModel):
    message: str = Field(min_length=1, max_length=4000)




def build_notifications(radios: list[dict], last_poll_result: str, queue_depth: int) -> list[dict]:
    """Prioritized, read-only operator warnings (no external delivery)."""
    alerts = []
    enabled = [r for r in radios if r.get("enabled")]
    if not enabled:
        alerts.append({"level": "critical", "message": "No radios enabled for broadcasting."})
    elif not any(r.get("connected") for r in enabled):
        alerts.append({"level": "critical", "message": "All enabled radios are disconnected."})
    elif any(not r.get("connected") for r in enabled):
        alerts.append({"level": "warning", "message": "One or more enabled radios are disconnected."})
    if str(last_poll_result).lower().startswith("error"):
        alerts.append({"level": "warning", "message": "Weather polling reported an error."})
    if queue_depth > 5:
        alerts.append({"level": "warning", "message": "Transmit queue has more than five pending messages."})
    for alert in alerts:
        alert["id"] = alert["message"].lower().replace(" ", "_").replace(".", "")[:90]
    return alerts


@router.get("/api/ux/notifications")
async def notifications(request: Request):
    tx = request.app.state.tx
    poller = request.app.state.poller
    return {"notifications": build_notifications(tx.status(), poller.status.last_poll_result, tx.queue_depth)}


@router.get("/api/ux/overview")
async def overview(request: Request):
    db = request.app.state.db
    tx = request.app.state.tx
    poller = request.app.state.poller
    radios = tx.status()
    enabled = [r for r in radios if r["enabled"]]
    connected = [r for r in enabled if r["connected"]]
    health = ("critical" if not connected else "degraded" if len(connected) < len(enabled) else "healthy")
    try:
        history = [dict(row) for row in db.query_history(limit=15)]
    except Exception:
        history = []
    try:
        broadcasts = [dict(row) for row in db.query_transmit_log(limit=15)]
    except Exception:
        broadcasts = []
    return {
        "health": health,
        "notifications": build_notifications(radios, poller.status.last_poll_result, tx.queue_depth),
        "radios": radios,
        "queue_depth": tx.queue_depth,
        "uptime_seconds": poller.status.uptime_seconds,
        "last_poll": poller.status.last_poll_time,
        "last_poll_result": poller.status.last_poll_result,
        "last_error": tx.last_error,
        "weather_history": history,
        "broadcast_history": broadcasts,
        "connection_history": tx.connection_history() if callable(getattr(tx, "connection_history", None)) else [],
        "dry_run": db.get_setting("dry_run", True),
    }


@router.post("/api/ux/preview")
async def preview(payload: Preview):
    from ..config import MAX_PAYLOAD_BYTES
    encoded = payload.message.encode("utf-8")
    clipped = payload.message
    while len(clipped.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        clipped = clipped[:-1]
    return {
        "preview": clipped,
        "bytes": len(encoded),
        "limit": MAX_PAYLOAD_BYTES,
        "truncated": clipped != payload.message,
        "transmitted": False,
    }


@router.get("/api/ux/preferences")
async def preferences(request: Request):
    db = request.app.state.db
    return {k: str(db.get_setting("ux_" + k, "true" if k.startswith("show_") else "false")).lower() in ("true", "1", "yes")
            for k in Preferences.model_fields}


@router.post("/api/ux/preferences")
async def save_preferences(request: Request, values: Preferences):
    db = request.app.state.db
    for key, value in values.model_dump().items():
        db.set_setting("ux_" + key, value)
    return values.model_dump()


@router.get("/operator", response_class=HTMLResponse)
async def operator():
    from pathlib import Path
    page = Path(__file__).parent / "templates" / "operator.html"
    return HTMLResponse(page.read_text(encoding="utf-8"))


@router.get("/operator/manifest.webmanifest")
async def manifest():
    return JSONResponse({"name":"WXCOMMAND-PRO Operator Center","short_name":"WXCOMMAND-PRO","start_url":"/operator","display":"standalone","background_color":"#101a22","theme_color":"#101a22"},media_type="application/manifest+json")


@router.get("/api/ux/map")
async def weather_map():
    """Display-only NWS active warning polygons, not the broadcast source."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.get("https://api.weather.gov/alerts/active", params={"limit": 100}, headers={"User-Agent": "WXCOMMAND-PRO (operator map; contact: project GitHub repository)", "Accept": "application/geo+json"})
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="NWS map unavailable") from exc
    features = []
    for item in data.get("features", []):
        if not isinstance(item, dict):
            continue
        geometry = item.get("geometry")
        if isinstance(geometry, dict) and geometry.get("type") in ("Polygon", "MultiPolygon"):
            props = item.get("properties") or {}
            features.append({"type": "Feature", "geometry": geometry, "properties": {k: props.get(k) for k in ("event", "severity", "areaDesc", "expires")}})
    return {"type": "FeatureCollection", "features": features, "limited": True}


@router.get("/api/ux/diagnostics")
async def diagnostics(request: Request):
    """Read-only diagnostic summary; never expose stored credentials."""
    db = request.app.state.db
    tx = request.app.state.tx
    poller = request.app.state.poller
    return {
        "radio_connections": [
            {"name": radio["name"], "enabled": radio["enabled"],
             "connected": radio["connected"], "connection": radio["conn"]}
            for radio in tx.status()
        ],
        "queue_depth": tx.queue_depth,
        "last_weather_poll": poller.status.last_poll_time,
        "weather_poll_result": poller.status.last_poll_result,
        "dry_run": db.get_setting("dry_run", True),
        "uptime_seconds": poller.status.uptime_seconds,
    }


class NotificationAck(BaseModel):
    id: str = Field(min_length=1, max_length=90)


@router.post("/api/ux/notifications/ack")
async def acknowledge_notification(request: Request, payload: NotificationAck):
    tx = request.app.state.tx
    poller = request.app.state.poller
    active = build_notifications(tx.status(), poller.status.last_poll_result, tx.queue_depth)
    if not any(item["id"] == payload.id for item in active):
        raise HTTPException(status_code=404, detail="Notification is not active")
    request.app.state.db.set_setting("ux_ack_" + payload.id,
                                     datetime.now(timezone.utc).isoformat())
    return {"acknowledged": payload.id}


@router.get("/api/ux/notifications/history")
async def notification_history(request: Request):
    db = request.app.state.db
    tx = request.app.state.tx
    poller = request.app.state.poller
    active = build_notifications(tx.status(), poller.status.last_poll_result, tx.queue_depth)
    for item in active:
        item["acknowledged_at"] = db.get_setting("ux_ack_" + item["id"], None)
    return {"notifications": active, "note": "Acknowledgements persist; resolved warnings are not retained."}


@router.get("/demo", response_class=HTMLResponse)
async def demonstration():
    """Fully isolated static showcase: no hardware, network, or database reads."""
    from pathlib import Path
    return HTMLResponse((Path(__file__).parent / "templates" / "demo.html").read_text(encoding="utf-8"))
