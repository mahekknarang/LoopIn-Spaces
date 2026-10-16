"""Small settings file for LoopIn: Spaces."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

def _load_local_env():
    """Load ignored .env settings without an extra runtime dependency."""
    env_file = BASE_DIR / ".env"
    if not env_file.is_file():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, separator, value = line.partition("=")
        if separator and key.strip():
            value = value.strip().strip("\"'")
            os.environ.setdefault(key.strip(), value)

_load_local_env()

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
# ADMIN_PIN remains a compatibility fallback for existing local/Render setups.
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", os.environ.get("ADMIN_PIN", "1234"))
SLOTS = ["7:45-8:40", "8:45-9:40", "9:45-10:40", "11:15-12:10", "12:15-1:10", "1:15-2:10", "2:45-3:40", "3:45-4:40", "4:45-5:40", "5:45-6:40"]
# The timetable has two long breaks between periods; bookings cannot span either one.
SLOT_BREAKS = [(SLOTS[2], SLOTS[3]), (SLOTS[5], SLOTS[6])]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
