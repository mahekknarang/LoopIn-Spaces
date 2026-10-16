"""A basic linked queue keeps pending requests in arrival order."""

class _Node:
    def __init__(self, value):
        """Keep one request and a link to the next queue item."""
        self.value, self.next = value, None

class Queue:
    def __init__(self):
        """Track both ends so adding a request stays quick."""
        self.front = self.rear = None
        self._size = 0

    def enqueue(self, value):
        """Add a new request at the back of the line."""
        node = _Node(value)
        if self.rear:
            self.rear.next = node
        else:
            self.front = node
        self.rear = node
        self._size += 1

    def dequeue(self):
        """Take the oldest request from the front of the line."""
        if self.is_empty():
            return None
        value = self.front.value
        self.front = self.front.next
        self._size -= 1
        if self.front is None:
            self.rear = None
        return value

    def peek(self):
        """Look at the oldest request without removing it."""
        return self.front.value if self.front else None

    def is_empty(self):
        """Check whether anyone is waiting."""
        return self.front is None

    def size(self):
        """Return the number of waiting items."""
        return self._size

    def remove(self, request_id):
        """Remove one request by ID and keep the other requests in order."""
        items = self.to_list()
        kept = [item for item in items if item.get("id") != request_id]
        self.front = self.rear = None
        self._size = 0
        for item in kept:
            self.enqueue(item)
        return len(kept) != len(items)

    def to_list(self):
        """Copy queue items into a list so the app can rebuild the queue."""
        result, node = [], self.front
        while node:
            result.append(node.value)
            node = node.next
        return result
