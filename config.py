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

ADMIN_PIN = os.environ.get("ADMIN_PIN", "1234")  # Override for deployed environments.
SLOTS = ["9-10", "10-11", "11-12", "12-1", "2-3", "3-4", "4-5"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
