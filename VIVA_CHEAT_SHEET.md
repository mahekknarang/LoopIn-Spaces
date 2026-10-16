# LoopIn: Spaces — viva cheat sheet

1. **What does the hash map do?** It connects a key, such as venue and weekday, to timetable data for a quick lookup. A normal dictionary lookup is O(1) on average.
2. **Why use a queue?** Requests should be considered first come, first served. Enqueue and dequeue are O(1) with front and rear nodes.
3. **How is the queue built?** Each node points to the next node. The app reads pending requests from JSON when it starts and puts them in order.
4. **What does merge sort do?** It splits a list, sorts each half, and merges them. Its time complexity is O(n log n).
5. **What is the sliding window?** It checks a moving group of consecutive periods to find a run of the requested length. It stops at the long campus breaks between timetable periods.
6. **What is greedy best fit?** It picks the smallest room that fits the group and time request, saving larger rooms. Sorting candidates takes O(n log n).
7. **What is a trie?** A tree of letters that can find names from a prefix. It powers room-name search.
8. **How does the app avoid a booking clash?** Before approval, it checks every requested slot against lectures and already approved bookings.
9. **Why do pending requests not reserve a room?** Only an admin approval blocks a slot. This lets the admin choose fairly and automatically reject overlapping pending requests after approval.
10. **Why save data in JSON?** It is easy to inspect and replace for a small project. A lock and atomic file replacement help prevent partial writes.
