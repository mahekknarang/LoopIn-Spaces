"""JSON storage uses a lock and atomic replace to protect each write."""
import json
import os
import threading
import urllib.parse
import urllib.request
from contextlib import contextmanager
from config import DATA_DIR

_file_lock = threading.RLock()

def _supabase_request(method, name, value=None):
    """Store JSON in Supabase when configured; credentials stay server-side."""
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        return None
    if key.startswith("sb_publishable_"):
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY must contain the Supabase Secret key, not the Publishable key.")
    query = urllib.parse.urlencode({"name": "eq." + name, "select": "data"})
    endpoint = url + "/rest/v1/spaces_store?" + query
    headers = {"apikey": key, "Accept": "application/json"}
    # New sb_secret keys are opaque API keys, not JWTs. Legacy service_role keys are JWTs.
    if not key.startswith("sb_secret_"):
        headers["Authorization"] = "Bearer " + key
    if method == "GET":
        req = urllib.request.Request(endpoint, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as response:
            rows = json.loads(response.read().decode("utf-8"))
        return rows[0]["data"] if rows else None
    headers.update({"Content-Type": "application/json", "Prefer": "resolution=merge-duplicates,return=minimal"})
    endpoint = url + "/rest/v1/spaces_store?on_conflict=name"
    payload = json.dumps({"name": name, "data": value}).encode("utf-8")
    req = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=8) as response:
        response.read()
    return True

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
    """Read one JSON file while no other thread is replacing it."""
    remote_enabled = bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        remote = _supabase_request("GET", name)
        if remote is not None:
            return remote
    with _file_lock, _process_file_lock():
        with (DATA_DIR / (name + ".json")).open(encoding="utf-8") as file:
            value = json.load(file)
    if remote_enabled:
        _supabase_request("POST", name, value)
    return value

def write_json(name, value):
    """Write a full JSON copy first, then swap it into place safely."""
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        _supabase_request("POST", name, value)
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
