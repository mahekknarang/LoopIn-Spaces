"""Small helpers for request IDs and pending-request FIFO ordering."""
from dsa.queue_ds import Queue
from dsa.sorting import merge_sort

def pending_queue(bookings):
    queue = Queue()
    waiting = merge_sort([item for item in bookings if item["status"] == "Pending"], lambda item: item["created_at"])
    for booking in waiting:
        queue.enqueue(booking)
    return queue

def next_request_id(bookings):
    highest = 1023
    for booking in bookings:
        try:
            highest = max(highest, int(booking["id"].split("-")[1]))
        except (ValueError, IndexError):
            continue
    return f"BK-{highest + 1}"
