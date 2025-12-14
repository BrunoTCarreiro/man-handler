from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field

from . import settings


class Device(BaseModel):
    id: str
    name: str
    brand: Optional[str] = None
    model: Optional[str] = None
    room: Optional[str] = None
    category: Optional[str] = None
    manual_files: List[str] = Field(default_factory=list)


def _catalog_path() -> Path:
    return settings.DEVICE_CATALOG_PATH


def load_devices() -> List[Device]:
    """Load device catalog from JSON; return empty list if file is missing."""
    path = _catalog_path()
    if not path.exists():
        return []
    import json

    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Device(**item) for item in raw]


def save_devices(devices: List[Device]) -> None:
    """Persist device catalog to JSON."""
    import json

    path = _catalog_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump([d.model_dump() for d in devices], f, indent=2, ensure_ascii=False)


def get_device(device_id: str) -> Optional[Device]:
    for device in load_devices():
        if device.id == device_id:
            return device
    return None


def list_rooms() -> List[str]:
    rooms = {d.room for d in load_devices() if d.room}
    return sorted(rooms)


