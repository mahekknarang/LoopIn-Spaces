"""Local JSON storage and normalized Supabase persistence."""
import json
import os
import threading
import urllib.parse
import urllib.request
from contextlib import contextmanager
from config import DATA_DIR

_file_lock = threading.RLock()


def _supabase_request(path, method="GET", payload=None):
    """Call the Supabase REST API using a server-only Secret/service-role key."""
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        return None
    if key.startswith("sb_publishable_"):
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY must contain the Supabase Secret key, not the Publishable key.")
    headers = {"apikey": key, "Accept": "application/json"}
    if not key.startswith("sb_secret_"):
        headers["Authorization"] = "Bearer " + key
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url + "/rest/v1/" + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=12) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else None


def _read_supabase(name):
    if name == "venues":
        rows = _supabase_request("venues?select=name,type,capacity,bookable&order=name")
        return [{"name": row["name"], "type": row["type"], "capacity": row["capacity"], "bookable": row["bookable"]} for row in rows]
    if name == "timetable":
        rows = _supabase_request("timetable?select=venue_name,day,slot,lecture&order=venue_name,day,slot")
        return [{"venue": row["venue_name"], "day": row["day"], "slot": row["slot"], "lecture": row["lecture"]} for row in rows]
    if name == "bookings":
        rows = _supabase_request("bookings?select=id,name,contact,event_name,purpose,venue_name,booking_date,status,reason,created_at,approved_at&order=created_at")
        if not rows:
            return []
        ids = [row["id"] for row in rows]
        encoded_ids = ",".join('"{}"'.format(value.replace('"', '\\"')) for value in ids)
        slots = _supabase_request("booking_slots?select=booking_id,slot&booking_id=in.({})".format(urllib.parse.quote(encoded_ids, safe=",\"")))
        by_booking = {}
        for row in slots:
            by_booking.setdefault(row["booking_id"], []).append(row["slot"])
        result = []
        for row in rows:
            result.append({"id": row["id"], "name": row["name"], "contact": row["contact"], "event": row["event_name"],
                           "purpose": row["purpose"], "venue": row["venue_name"], "date": row["booking_date"],
                           "slots": by_booking.get(row["id"], []), "status": row["status"], "reason": row["reason"] or "",
                           "created_at": row["created_at"], "approved_at": row["approved_at"]})
        return result
    raise ValueError("Unknown data collection: {}".format(name))


def _write_supabase(name, value):
    functions = {"venues": "loopin_save_venues", "timetable": "loopin_save_timetable", "bookings": "loopin_save_bookings"}
    if name not in functions:
        raise ValueError("Unknown data collection: {}".format(name))
    _supabase_request("rpc/" + functions[name], method="POST", payload={"p_data": value})


@contextmanager
def _process_file_lock():
    """Hold a small OS file lock so separate app processes do not collide."""
    DATA_DIR.mkdir(exist_ok=True)
    lock_path = DATA_DIR / ".storage.lock"
    with lock_path.open("a+") as lock_file:
        if os.name == "nt":
            import msvcrt
            lock_file.seek(0, os.SEEK_END)
            if lock_file.tell() == 0:
                lock_file.write("0")
                lock_file.flush()
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def read_json(name):
    """Read a collection from Supabase, or the local JSON file if unconfigured."""
    remote_enabled = bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))
    if remote_enabled:
        # An empty remote table is a legitimate value; never seed it from stale local demo files.
        return _read_supabase(name)
    with _file_lock, _process_file_lock():
        with (DATA_DIR / (name + ".json")).open(encoding="utf-8") as file:
            return json.load(file)


def write_json(name, value):
    """Persist one collection atomically (SQL function on Supabase, file locally)."""
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        _write_supabase(name, value)
        return
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / (name + ".json")
    temporary = path.with_name("{}.{}.{}.tmp".format(path.stem, os.getpid(), threading.get_ident()))
    with _file_lock, _process_file_lock():
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(value, file, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(str(temporary), str(path))
