"""Central rules for whether a date-specific venue slot can be requested."""
from datetime import date
from config import SLOTS, SLOT_BREAKS
from dsa.hash_map_store import HashMapStore

def slot_status(venue, day, date_text, slot, timetable, bookings):
    store = HashMapStore(timetable=timetable)
    lecture = store.lecture_at(venue, day, slot)
    if lecture:
        return {"state": "lecture", "label": lecture}
    for booking in bookings:
        if booking["venue"] == venue and booking["date"] == date_text and booking["status"] == "Approved" and slot in booking["slots"]:
            return {"state": "approved", "label": booking["event"]}
    for booking in bookings:
        if booking["venue"] == venue and booking["date"] == date_text and booking["status"] == "Pending" and slot in booking["slots"]:
            return {"state": "pending", "label": "Pending request"}
    return {"state": "free", "label": "Free"}

def check_request(payload, venues, timetable, bookings):
    required = ["name", "contact", "event", "purpose", "venue", "date", "start", "end"]
    if any(not isinstance(payload.get(key), str) or not payload[key].strip() for key in required):
        return "Please fill in every field."
    try:
        target = date.fromisoformat(payload["date"])
    except ValueError:
        return "Choose a valid date."
    if target < date.today():
        return "That date has already passed. Pick a future date."
    venue_index = HashMapStore(venues=venues).venues
    if payload["venue"] not in venue_index:
        return "Choose a venue from the list."
    if payload["start"] not in SLOTS or payload["end"] not in SLOTS:
        return "Choose valid start and end times."
    start, end = SLOTS.index(payload["start"]), SLOTS.index(payload["end"])
    if start > end:
        return "End time must come after start time."
    chosen = SLOTS[start:end + 1]
    # Adjacent timetable periods separated by a long campus break are not continuous.
    for before, after in SLOT_BREAKS:
        if before in chosen and after in chosen:
            return "Bookings can’t cross a break between timetable periods."
    day = target.strftime("%A")
    for slot in chosen:
        result = slot_status(payload["venue"], day, payload["date"], slot, timetable, bookings)
        if result["state"] == "lecture":
            return f"{payload['venue']} has {result['label']} during {slot}. Try another time."
        if result["state"] == "approved":
            return "That slot was just taken. Try another time."
    return None

def request_slots(payload):
    return SLOTS[SLOTS.index(payload["start"]):SLOTS.index(payload["end"]) + 1]
