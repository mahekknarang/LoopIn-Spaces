import unittest
from dsa.queue_ds import Queue
from dsa.sliding_window import find_windows
from logic.slot_checker import check_request
from config import SLOTS
from dsa.greedy_best_fit import best_fit
from unittest.mock import patch
import app as spaces_app

class QueueTests(unittest.TestCase):
    def test_fifo_and_empty_operations(self):
        queue = Queue()
        self.assertTrue(queue.is_empty())
        self.assertIsNone(queue.peek())
        self.assertIsNone(queue.dequeue())
        queue.enqueue("first")
        queue.enqueue("second")
        self.assertEqual(queue.peek(), "first")
        self.assertEqual(queue.dequeue(), "first")
        self.assertEqual(queue.dequeue(), "second")
        self.assertTrue(queue.is_empty())

    def test_remove_and_size(self):
        queue = Queue()
        queue.enqueue({"id": "BK-1"})
        queue.enqueue({"id": "BK-2"})
        self.assertEqual(queue.size(), 2)
        self.assertTrue(queue.remove("BK-1"))
        self.assertEqual([item["id"] for item in queue.to_list()], ["BK-2"])

class SlidingWindowTests(unittest.TestCase):
    def test_finds_only_consecutive_slots_and_skips_lunch(self):
        free = ["9:45-10:40", "11:15-12:10", "12:15-1:10", "1:15-2:10", "2:45-3:40", "3:45-4:40", "4:45-5:40"]
        self.assertEqual(find_windows(free, SLOTS, 2), [["11:15-12:10", "12:15-1:10"], ["12:15-1:10", "1:15-2:10"], ["2:45-3:40", "3:45-4:40"], ["3:45-4:40", "4:45-5:40"]])

    def test_lunch_does_not_make_a_two_hour_window(self):
        self.assertEqual(find_windows(["1:15-2:10", "2:45-3:40"], SLOTS, 2), [])

class GreedyTests(unittest.TestCase):
    def test_chooses_smallest_room_that_fits(self):
        venues = [{"name":"Hall", "capacity":100}, {"name":"LR", "capacity":30}, {"name":"Lab", "capacity":20}]
        self.assertEqual(best_fit(venues, 25)["name"], "LR")

class ClashCheckerTests(unittest.TestCase):
    def setUp(self):
        self.venues = [{"name":"LR 1", "capacity":40}]
        self.timetable = [{"venue":"LR 1", "day":"Monday", "slot":SLOTS[0], "lecture":"DSA"}]
        self.bookings = []
        self.payload = {"name":"A", "contact":"a@college.edu", "event":"Meet", "purpose":"Club", "venue":"LR 1", "date":"2099-10-19", "start":SLOTS[0], "end":SLOTS[0]}

    def test_lecture_clash_is_friendly(self):
        self.assertIn("DSA", check_request(self.payload, self.venues, self.timetable, self.bookings))

    def test_approved_booking_clash(self):
        self.timetable = []
        self.bookings = [{"venue":"LR 1", "date":"2099-10-19", "slots":[SLOTS[0]], "status":"Approved", "event":"Meet"}]
        self.assertIn("taken", check_request(self.payload, self.venues, self.timetable, self.bookings))

    def test_pending_request_does_not_block_another_request(self):
        self.timetable = []
        self.bookings = [{"venue":"LR 1", "date":"2099-10-19", "slots":[SLOTS[0]], "status":"Pending", "event":"Meet"}]
        self.assertIsNone(check_request(self.payload, self.venues, self.timetable, self.bookings))

    def test_lunch_break_is_not_bookable_across(self):
        self.payload.update(start="1:15-2:10", end="2:45-3:40")
        self.assertIn("break", check_request(self.payload, self.venues, [], []))

    def test_library_booking_needs_special_permission(self):
        self.venues = [{"name":"XICA LIBRARY", "capacity":60, "bookable":False}]
        self.payload["venue"] = "XICA LIBRARY"
        self.assertIn("special permission", check_request(self.payload, self.venues, [], []))

    def test_admin_enabled_library_can_be_requested(self):
        self.venues = [{"name":"XICA LIBRARY", "capacity":60, "bookable":True}]
        self.payload["venue"] = "XICA LIBRARY"
        self.assertIsNone(check_request(self.payload, self.venues, [], []))

class ApprovalTests(unittest.TestCase):
    def test_approval_rejects_other_pending_clash(self):
        date_text = "2099-10-19"
        bookings = [
            {"id":"BK-2001", "name":"One", "contact":"x", "event":"First", "purpose":"Meet", "venue":"LR 1", "date":date_text, "slots":[SLOTS[-1]], "status":"Pending", "created_at":"2099-01-01T09:00:00"},
            {"id":"BK-2002", "name":"Two", "contact":"x", "event":"Second", "purpose":"Meet", "venue":"LR 1", "date":date_text, "slots":[SLOTS[-1]], "status":"Pending", "created_at":"2099-01-01T09:01:00"},
        ]
        data = {"bookings": bookings, "venues":[{"name":"LR 1", "capacity":40}], "timetable":[]}
        def load(name): return data[name]
        def save(name, value): data[name] = value
        client = spaces_app.app.test_client()
        with patch.object(spaces_app, "load_data", side_effect=load), patch.object(spaces_app, "save_data", side_effect=save):
            with client.session_transaction() as session:
                session["admin"] = True
            response = client.post("/api/admin/requests/BK-2001", json={"decision":"approve"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["bookings"][0]["status"], "Approved")
        self.assertEqual(data["bookings"][1]["status"], "Rejected")
        self.assertEqual(data["bookings"][1]["reason"], "Slot already taken")

class VenuePermissionRouteTests(unittest.TestCase):
    def setUp(self):
        self.data = {
            "venues": [{"name":"XICA LIBRARY", "type":"Library", "capacity":60, "bookable":False}],
            "timetable": [],
            "bookings": [],
        }
        self.client = spaces_app.app.test_client()

    def test_grid_marks_library_as_restricted(self):
        with patch.object(spaces_app, "load_data", side_effect=lambda name: self.data[name]):
            response = self.client.get("/api/grid?date=2099-10-19")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["grid"]["XICA LIBRARY"][SLOTS[0]]["state"], "restricted")

    def test_public_booking_is_rejected_without_permission(self):
        payload = {"name":"A", "contact":"a@college.edu", "event":"Study", "purpose":"Study group",
                   "venue":"XICA LIBRARY", "date":"2099-10-19", "start":SLOTS[0], "end":SLOTS[0]}
        with patch.object(spaces_app, "load_data", side_effect=lambda name: self.data[name]):
            response = self.client.post("/api/requests", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("special permission", response.json["error"])

    def test_admin_can_enable_library_after_permission(self):
        def save(name, value): self.data[name] = value
        with patch.object(spaces_app, "load_data", side_effect=lambda name: self.data[name]), patch.object(spaces_app, "save_data", side_effect=save):
            with self.client.session_transaction() as session:
                session["admin"] = True
            response = self.client.put("/api/admin/venues", json={"name":"XICA LIBRARY", "new_name":"XICA LIBRARY",
                "type":"Library", "capacity":60, "bookable":True})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.data["venues"][0]["bookable"])

if __name__ == "__main__":
    unittest.main()
