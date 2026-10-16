"""Small settings file for LoopIn: Spaces."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ADMIN_PIN = "1234"  # Change this before sharing the demo.
SLOTS = ["9-10", "10-11", "11-12", "12-1", "2-3", "3-4", "4-5"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
