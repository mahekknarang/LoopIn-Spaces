"""LoopIn: Spaces — a JSON-backed college venue planner."""
import json
import os
import socket
import time
from datetime import date, datetime, timedelta
from functools import wraps
from flask import Flask, jsonify, render_template, request, session
from config import BASE_DIR, DATA_DIR, SLOTS, DAYS, ADMIN_PIN
from logic.slot_checker import slot_status, check_request, request_slots
from logic.booking_manager import pending_queue, next_request_id
from logic.storage import read_json, write_json
from logic.timetable_pdf import extract_college_timetable
from dsa.sorting import sort_history, sort_slots, merge_sort
from dsa.greedy_best_fit import best_fit
from dsa.sliding_window import find_windows
from dsa.trie import Trie
from dsa.hash_map_store import HashMapStore

app = Flask(__name__)
app.secret_key = os.environ.get("LOOPIN_SECRET_KEY", "loopin-local-demo-secret-change-me")
PENDING_QUEUE = None

def load_data(name):
    return read_json(name)

def save_data(name, data):
    write_json(name, data)

def rebuild_pending_queue():
    """Rebuild the first-come queue from the saved JSON requests."""
    global PENDING_QUEUE
    PENDING_QUEUE = pending_queue(load_data("bookings"))

rebuild_pending_queue()

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("admin"):
            return jsonify({"error": "Admin PIN required."}), 401
        return fn(*args, **kwargs)
    return wrapped

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/book")
def book_page():
    return render_template("book.html")

@app.get("/status")
def status_page():
    return render_template("status.html")

@app.get("/admin")
def admin_page():
    return render_template("admin.html")

@app.get("/how-it-works")
def how_it_works():
    return render_template("how.html")

@app.get("/api/bootstrap")
def bootstrap():
    venues, timetable, bookings = load_data("venues"), load_data("timetable"), load_data("bookings")
    today = date.today().isoformat()
    day = date.today().strftime("%A")
    grid = {v["name"]: {s: slot_status(v["name"], day, today, s, timetable, bookings) for s in SLOTS} for v in venues}
    pending = [b for b in bookings if b["status"] == "Pending"]
    return jsonify({"venues": venues, "timetable": timetable, "slots": sort_slots(SLOTS, SLOTS), "days": DAYS,
                    "today": today, "today_day": day, "today_grid": grid,
                    "pending_count": len(pending), "queue_first": pending_queue(bookings).peek() is not None})

@app.get("/api/grid")
def grid():
    date_text = request.args.get("date", "")
    try:
        day = date.fromisoformat(date_text).strftime("%A")
    except ValueError:
        return jsonify({"error": "Choose a valid date."}), 400
    venues, timetable, bookings = load_data("venues"), load_data("timetable"), load_data("bookings")
    result = {v["name"]: {s: slot_status(v["name"], day, date_text, s, timetable, bookings) for s in SLOTS} for v in venues}
    return jsonify({"grid": result, "venues": venues, "slots": sort_slots(SLOTS, SLOTS), "day": day})

@app.get("/api/venues/search")
def search_venues():
    venues = load_data("venues")
    names = Trie(v["name"] for v in venues).search(request.args.get("q", ""))
    return jsonify({"names": names})

@app.post("/api/requests")
def create_request():
    payload = request.get_json(silent=True) or {}
    venues, timetable, bookings = load_data("venues"), load_data("timetable"), load_data("bookings")
    error = check_request(payload, venues, timetable, bookings)
    if error:
        return jsonify({"error": error}), 400
    record = {**{key: payload[key].strip() for key in ("name", "contact", "event", "purpose", "venue", "date")},
              "id": next_request_id(bookings), "slots": request_slots(payload), "status": "Pending",
              "created_at": datetime.now().isoformat(timespec="seconds")}
    bookings.append(record)
    save_data("bookings", bookings)
    rebuild_pending_queue()
    return jsonify(record), 201

@app.get("/api/requests/<request_id>")
def get_request(request_id):
    bookings = load_data("bookings")
    store = HashMapStore(bookings=bookings)
    item = store.booking(request_id)
    if item is None:
        item = next((booking for booking in bookings if booking["id"].lower() == request_id.lower()), None)
    if not item:
        return jsonify({"error": "We couldn’t find that ID. Double-check it?"}), 404
    public_fields = {key: item[key] for key in ("id", "status", "event", "venue", "date", "slots") if key in item}
    if item.get("reason"):
        public_fields["reason"] = item["reason"]
    return jsonify(public_fields)

@app.post("/api/find")
def find_venue():
    payload = request.get_json(silent=True) or {}
    try:
        target = date.fromisoformat(payload.get("date", ""))
        people, hours = int(payload.get("people", 0)), int(payload.get("hours", 0))
        if target < date.today() or people < 1 or hours < 1 or hours > 7:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "Choose a future date, a positive group size, and 1–7 hours."}), 400
    venues, timetable, bookings = load_data("venues"), load_data("timetable"), load_data("bookings")
    day, results = target.strftime("%A"), []
    for venue in venues:
        if venue["capacity"] < people:
            continue
        free = [s for s in SLOTS if slot_status(venue["name"], day, payload["date"], s, timetable, bookings)["state"] in ("free", "pending")]
        for window in find_windows(free, SLOTS, hours):
            results.append({"venue": venue, "slots": window})
    results = merge_sort(results, lambda item: item["venue"]["capacity"])
    fit = best_fit([item["venue"] for item in results], people)
    best_name = fit["name"] if fit else None
    return jsonify({"results": results, "best": best_name})

@app.post("/api/admin/login")
def admin_login():
    pin = str((request.get_json(silent=True) or {}).get("pin", ""))
    now = time.time()
    blocked_until = session.get("pin_blocked_until", 0)
    if now < blocked_until:
        return jsonify({"error": "Too many attempts. Try again in one minute."}), 429
    if pin == ADMIN_PIN:
        session["admin"] = True
        session.pop("pin_failures", None)
        session.pop("pin_blocked_until", None)
        return jsonify({"ok": True})
    failures = session.get("pin_failures", 0) + 1
    session["pin_failures"] = failures
    if failures >= 5:
        session["pin_failures"] = 0
        session["pin_blocked_until"] = now + 60
        return jsonify({"error": "Too many attempts. Try again in one minute."}), 429
    return jsonify({"error": "That PIN didn’t match."}), 401

@app.post("/api/admin/logout")
@admin_required
def admin_logout():
    session.pop("admin", None)
    return jsonify({"ok": True})

@app.get("/api/admin/data")
@admin_required
def admin_data():
    bookings = load_data("bookings")
    queue = PENDING_QUEUE or pending_queue(bookings)
    return jsonify({"venues": load_data("venues"), "timetable": load_data("timetable"),
                    "requests": queue.to_list(), "history": sort_history([b for b in bookings if b["status"] != "Pending"]), "slots": SLOTS, "days": DAYS})

@app.post("/api/admin/requests/<request_id>")
@admin_required
def decide_request(request_id):
    payload = request.get_json(silent=True) or {}
    bookings = load_data("bookings")
    item = next((b for b in bookings if b["id"] == request_id), None)
    if not item or item["status"] != "Pending":
        return jsonify({"error": "That pending request is no longer available."}), 404
    decision = payload.get("decision")
    if decision == "reject":
        reason = str(payload.get("reason", "")).strip()
        if not reason:
            return jsonify({"error": "Add a short rejection reason."}), 400
        item.update(status="Rejected", reason=reason)
    elif decision == "approve":
        venues, timetable = load_data("venues"), load_data("timetable")
        day = date.fromisoformat(item["date"]).strftime("%A")
        for slot in item["slots"]:
            if slot_status(item["venue"], day, item["date"], slot, timetable, bookings)["state"] in ("lecture", "approved"):
                return jsonify({"error": "Clash detected. This request can’t be approved now."}), 409
        item.update(status="Approved", reason="", approved_at=datetime.now().isoformat(timespec="seconds"))
        for other in bookings:
            if other["status"] == "Pending" and other["id"] != item["id"] and other["venue"] == item["venue"] and other["date"] == item["date"] and set(other["slots"]) & set(item["slots"]):
                other.update(status="Rejected", reason="Slot already taken")
    else:
        return jsonify({"error": "Choose approve or reject."}), 400
    save_data("bookings", bookings)
    rebuild_pending_queue()
    return jsonify({"ok": True})

@app.post("/api/admin/timetable")
@admin_required
def timetable_edit():
    payload = request.get_json(silent=True) or {}
    rows = load_data("timetable")
    key = (payload.get("venue"), payload.get("day"), payload.get("slot"))
    if key[0] not in {v["name"] for v in load_data("venues")} or key[1] not in DAYS or key[2] not in SLOTS:
        return jsonify({"error": "Choose a valid venue, day, and slot."}), 400
    lecture_name = str(payload.get("lecture", "")).strip()
    existing = any((r["venue"], r["day"], r["slot"]) == key for r in rows)
    if lecture_name and existing and not payload.get("replace", False):
        return jsonify({"error": "A lecture already uses that venue, day, and slot."}), 409
    rows = [r for r in rows if (r["venue"], r["day"], r["slot"]) != key]
    if lecture_name:
        rows.append({"venue": key[0], "day": key[1], "slot": key[2], "lecture": lecture_name})
    save_data("timetable", rows)
    return jsonify({"ok": True})

@app.post("/api/admin/timetable/import")
@admin_required
def timetable_import():
    payload = request.get_json(silent=True) or {}
    imported = payload.get("rows")
    if not isinstance(imported, list) or not imported or len(imported) > 500:
        return jsonify({"error": "No timetable entries were recognized. The current timetable was kept."}), 400
    venue_names = {venue["name"] for venue in load_data("venues")}
    cleaned, seen = [], set()
    for item in imported:
        if not isinstance(item, dict):
            continue
        venue, day, slot = (item.get(field) for field in ("venue", "day", "slot"))
        lecture = str(item.get("lecture", "")).strip()[:100]
        key = (venue, day, slot)
        if venue not in venue_names or day not in DAYS or slot not in SLOTS or not lecture or key in seen:
            continue
        seen.add(key)
        cleaned.append({"venue": venue, "day": day, "slot": slot, "lecture": lecture})
    if not cleaned:
        return jsonify({"error": "No valid venue, day, time, and class entries were recognized. The current timetable was kept."}), 400
    save_data("timetable", cleaned)
    return jsonify({"ok": True, "count": len(cleaned)})

@app.post("/api/admin/timetable/import-pdf")
@admin_required
def timetable_import_pdf():
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Choose a timetable PDF file."}), 400
    try:
        venue_names = [venue["name"] for venue in load_data("venues")]
        rows = extract_college_timetable(uploaded.stream, venue_names)
    except Exception as error:
        message = str(error) if isinstance(error, ValueError) else "The PDF couldn’t be read. Try exporting the original timetable PDF again."
        return jsonify({"error": message}), 400
    save_data("timetable", rows)
    return jsonify({"ok": True, "count": len(rows), "day": rows[0]["day"]})

@app.route("/api/admin/venues", methods=["POST", "PUT", "DELETE"])
@admin_required
def venues_edit():
    payload = request.get_json(silent=True) or {}
    venues = load_data("venues")
    raw_name = payload.get("name", "")
    name = raw_name.strip() if isinstance(raw_name, str) else ""
    if request.method == "DELETE":
        if any(b["venue"] == name for b in load_data("bookings")):
            return jsonify({"error": "This venue has booking history. Keep it in the venue list so those records remain linked."}), 409
        venues = [v for v in venues if v["name"] != name]
        save_data("timetable", [r for r in load_data("timetable") if r["venue"] != name])
        save_data("venues", venues)
        return jsonify({"ok": True})
    try:
        raw_new_name, raw_kind = payload.get("new_name", name), payload["type"]
        if not isinstance(raw_new_name, str) or not isinstance(raw_kind, str):
            raise ValueError
        new_name, kind, capacity = raw_new_name.strip(), raw_kind.strip(), int(payload["capacity"])
        if not new_name or kind not in ("LR", "Lab", "Hall", "Library") or capacity < 1:
            raise ValueError
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "Enter a name, venue type, and positive capacity."}), 400
    if request.method == "PUT":
        target = next((v for v in venues if v["name"] == name), None)
        if not target:
            return jsonify({"error": "Venue not found."}), 404
        if new_name.lower() != name.lower() and any(v["name"].lower() == new_name.lower() for v in venues):
            return jsonify({"error": "A venue with that name already exists."}), 400
        if new_name != name:
            # Keep both names available while child rows move; the database
            # enforces venue references for timetable and booking records.
            old_venue = dict(target)
            target.update(name=new_name, type=kind, capacity=capacity)
            save_data("venues", venues + [old_venue])
            timetable = load_data("timetable")
            for row in timetable:
                if row["venue"] == name:
                    row["venue"] = new_name
            save_data("timetable", timetable)
            bookings = load_data("bookings")
            for booking in bookings:
                if booking["venue"] == name:
                    booking["venue"] = new_name
            save_data("bookings", bookings)
            rebuild_pending_queue()
        else:
            target.update(name=new_name, type=kind, capacity=capacity)
    else:
        if any(v["name"].lower() == new_name.lower() for v in venues):
            return jsonify({"error": "A venue with that name already exists."}), 400
        venues.append({"name": new_name, "type": kind, "capacity": capacity})
    save_data("venues", venues)
    return jsonify({"ok": True})

if __name__ == "__main__":
    DATA_DIR.mkdir(exist_ok=True)
    demo_bookings = load_data("bookings")
    for index, booking in enumerate(demo_bookings):
        if booking["id"] in ("BK-1024", "BK-1025", "BK-1026") and booking["status"] == "Pending":
            booking["date"] = (date.today() + timedelta(days=4 + index)).isoformat()
    save_data("bookings", demo_bookings)
    deployed_port = os.environ.get("PORT")
    if deployed_port:
        chosen_port, host = int(deployed_port), "0.0.0.0"
    else:
        chosen_port, host = 5000, "127.0.0.1"
        probe = socket.socket()
        try:
            probe.bind((host, chosen_port))
        except OSError:
            chosen_port = 5001
        finally:
            probe.close()
    print("LoopIn: Spaces is running at http://{}:{}".format("127.0.0.1" if host == "0.0.0.0" else host, chosen_port), flush=True)
    app.run(host=host, port=chosen_port, debug=False, use_reloader=False)
