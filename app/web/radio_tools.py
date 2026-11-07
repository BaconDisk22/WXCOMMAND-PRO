"""Saved radio configurations and a read-only radio tools dashboard.

Profiles are stored in the existing settings database; saving a profile does
not change the active radio configuration or transmit any messages.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

router = APIRouter()
_ALLOWED = ("meshtastic", "meshcore")
_CONN = ("serial", "tcp", "ble")


class RadioProfile(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    protocol: str
    connection: str
    target: str = Field(min_length=1, max_length=255)


def _profiles(db) -> list[dict]:
    raw = db.get_setting("radio_profiles", "[]")
    if isinstance(raw, list):
        return raw
    try:
        value = json.loads(raw)
        return value if isinstance(value, list) else []
    except (TypeError, ValueError):
        return []


@router.get("/api/radios/profiles")
async def list_profiles(request: Request):
    return {"profiles": _profiles(request.app.state.db)}


@router.post("/api/radios/profiles")
async def save_profile(request: Request, profile: RadioProfile):
    if profile.protocol not in _ALLOWED or profile.connection not in _CONN:
        raise HTTPException(status_code=422, detail="Invalid protocol or connection")
    db = request.app.state.db
    profiles = _profiles(db)
    item = profile.model_dump()
    profiles = [p for p in profiles if not (
        p.get("name") == item["name"] and p.get("protocol") == item["protocol"]
    )]
    if len(profiles) >= 20:
        raise HTTPException(status_code=422, detail="Maximum 20 saved profiles")
    profiles.append(item)
    db.set_setting("radio_profiles", json.dumps(profiles))
    return {"profiles": profiles}



class ProfileKey(BaseModel):
    name: str
    protocol: str


def _find_profile(db, key: ProfileKey) -> dict:
    match = next((p for p in _profiles(db) if p.get("name") == key.name
                  and p.get("protocol") == key.protocol), None)
    if match is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    if match.get("connection") not in _CONN or not match.get("target"):
        raise HTTPException(status_code=422, detail="Profile is invalid")
    return match


@router.delete("/api/radios/profiles")
async def delete_profile(request: Request, key: ProfileKey):
    db = request.app.state.db
    _find_profile(db, key)
    profiles = [p for p in _profiles(db) if not (
        p.get("name") == key.name and p.get("protocol") == key.protocol)]
    db.set_setting("radio_profiles", json.dumps(profiles))
    return {"profiles": profiles}


@router.post("/api/radios/profiles/activate")
async def activate_profile(request: Request, key: ProfileKey):
    """Apply a saved profile and reconnect radios using existing manager logic."""
    db = request.app.state.db
    profile = _find_profile(db, key)
    protocol, conn, target = profile["protocol"], profile["connection"], profile["target"]
    if protocol not in _ALLOWED:
        raise HTTPException(status_code=422, detail="Invalid protocol")
    prefix = "meshtastic" if protocol == "meshtastic" else "meshcore"
    db.set_setting(prefix + "_conn", conn)
    target_key = ("serial_port" if protocol == "meshtastic" else "meshcore_port") if conn == "serial" else prefix + "_host"
    db.set_setting(target_key, target)
    db.set_setting(prefix + "_enabled", True)
    await request.app.state.tx.reconfigure()
    return {"activated": profile, "radios": request.app.state.tx.status()}


@router.post("/api/radios/reconnect")
async def reconnect_radios(request: Request):
    """Manually refresh all configured connections, without sending."""
    await request.app.state.tx.reconfigure()
    return {"radios": request.app.state.tx.status()}


class FailoverSetting(BaseModel):
    enabled: bool


@router.get("/api/radios/failover")
async def get_failover(request: Request):
    value = request.app.state.db.get_setting("radio_failover_enabled", False)
    enabled = value.lower() in ("true", "1", "yes", "on") if isinstance(value, str) else bool(value)
    return {"enabled": enabled}


@router.post("/api/radios/failover")
async def set_failover(request: Request, setting: FailoverSetting):
    request.app.state.db.set_setting("radio_failover_enabled", setting.enabled)
    return {"enabled": setting.enabled}


@router.get("/settings/radio-tools", response_class=HTMLResponse)
async def radio_tools(request: Request):
    from .routes import render
    return render(request, "radio_tools.html")
