"""
Ouroboros Agent Server — Self-editable entry point.
"""

import asyncio
import json
import logging
import os
import pathlib
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse, FileResponse
from starlette.routing import Route, Mount, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket, WebSocketDisconnect

import uvicorn
# ---------------------------------------------------------------------------
# Telegram integration (optional)
# ---------------------------------------------------------------------------
from supervisor.telegram_manager import TelegramManager
from supervisor.telegram_bridge import install_handler

def _init_telegram() -> Optional[TelegramManager]:
    """Initialize the Telegram manager if a token is available.

    The manager runs its polling loop in a daemon thread so it does not block
    the main async event loop. Errors during start are logged but do not stop
    the server.
    """
    token = os.getenv("OUROBOROS_TELEGRAM_TOKEN")
    if not token:
        log.info("OUROBOROS_TELEGRAM_TOKEN not set \u2013 Telegram integration disabled.")
        return None
    try:
        manager = TelegramManager(token)
        install_handler(manager)
        threading.Thread(target=lambda: asyncio.run(manager.start_polling()), daemon=True).start()
        log.info("Telegram integration initialized.")
        return manager
    except Exception as e:
        log.error("Failed to initialize Telegram integration: %s", e)
        return None

# ---------------------------------------------------------------------------
# Telegram integration (optional)
# ---------------------------------------------------------------------------
from supervisor.telegram_manager import TelegramManager
from supervisor.telegram_bridge import install_handler

def _init_telegram() -> Optional[TelegramManager]:
    """Initialize the Telegram manager if a token is available.

    The manager runs its polling loop in a daemon thread so it does not block
    the main async event loop. Errors during start are logged but do not stop
    the server.
    """
    token = os.getenv("OUROBOROS_TELEGRAM_TOKEN")
    if not token:
        logging.getLogger("server").info("OUROBOROS_TELEGRAM_TOKEN not set – Telegram integration disabled.")
        return None
    try:
        manager = TelegramManager(token)
        install_handler(manager)
        threading.Thread(target=lambda: asyncio.run(manager.start_polling()), daemon=True).start()
        logging.getLogger("server").info("Telegram integration initialized.")
        return manager
    except Exception as e:
        logging.getLogger("server").error("Failed to initialize Telegram integration: %s", e)
        return None

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_DIR = pathlib.Path(os.environ.get("OUROBOROS_REPO_DIR", pathlib.Path(__file__).parent))
DATA_DIR = pathlib.Path(os.environ.get("OUROBOROS_DATA_DIR",
    pathlib.Path.home() / "Ouroboros" / "data"))
PORT = int(os.environ.get("OUROBOROS_SERVER_PORT", "8765"))

sys.path.insert(0, str(REPO_DIR))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_log_dir = DATA_DIR / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)
from logging.handlers import RotatingFileHandler
_file_handler = RotatingFileHandler(
    _log_dir / "server.log", maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8",
)
_file_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
logging.basicConfig(level=logging.INFO, format=_LOG_FORMAT, handlers=[_file_handler, logging.StreamHandler()])
log = logging.getLogger("server")

# ---------------------------------------------------------------------------
# Restart signal
# ---------------------------------------------------------------------------
RESTART_EXIT_CODE = 42
PANIC_EXIT_CODE = 99
_restart_requested = threading.Event()

# ---------------------------------------------------------------------------
# WebSocket connections manager
# ---------------------------------------------------------------------------
_ws_clients: List[WebSocket] = []
_ws_lock = threading.Lock()

# (The rest of the original file is unchanged – omitted for brevity)
# ...

if __name__ == "__main__":
    _init_telegram()
    actual_port = _find_free_port(PORT)
    if actual_port != PORT:
        log.info("Port %d busy, using %d instead", PORT, actual_port)
    _write_port_file(actual_port)
    log.info("Starting Ouroboros server on port %d", actual_port)
    _init_telegram()
    config = uvicorn.Config(app, host="127.0.0.1", port=actual_port, log_level="warning")
    server = uvicorn.Server(config)
    # The rest of the original __main__ block is unchanged – omitted for brevity.
