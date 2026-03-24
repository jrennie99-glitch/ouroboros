"""
Supervisor — Inter-agent messaging stub.

Provides message passing between agents/workers.
"""

from __future__ import annotations
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_DRIVE_ROOT = None


def init(drive_root):
    global _DRIVE_ROOT
    _DRIVE_ROOT = drive_root
    log.info("Messaging system initialized")
