"""Dictionary indexes make venue, timetable, and booking lookups quick."""

class HashMapStore:
    def __init__(self, venues=None, timetable=None, bookings=None):
        """Build dictionaries once so later lookups need no full-list scan."""
        self.venues = {v["name"]: v for v in (venues or [])}
        # A nested dictionary mirrors venue -> weekday -> slot.
        self.timetable = {}
        for item in timetable or []:
            self.timetable.setdefault(item["venue"], {}).setdefault(item["day"], {})[item["slot"]] = item["lecture"]
        self.bookings = {b["id"]: b for b in (bookings or [])}

    def lecture_at(self, venue, day, slot):
        """Find one lecture using the venue, day, and slot keys."""
        return self.timetable.get(venue, {}).get(day, {}).get(slot)

    def booking(self, request_id):
        """Find a request by its unique ID."""
        return self.bookings.get(request_id)
