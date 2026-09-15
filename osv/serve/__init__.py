"""FastAPI server and WebRTC/WebSocket streaming engine for surgical video overlays."""

from typing import Any


def get_server_metadata() -> dict[str, Any]:
    """Returns server metadata including mandatory non-clinical disclaimer."""
    return {
        "service": "OpenSurgicalVision Demo Server",
        "disclaimer": "RESEARCH USE ONLY — NOT FOR CLINICAL USE",
        "status": "ready",
    }


__all__ = ["get_server_metadata"]
