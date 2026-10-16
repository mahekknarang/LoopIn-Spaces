"""A moving window finds consecutive free slots without crossing lunch."""

def find_windows(free_slots, slots, hours):
    """Return every run of free slots that is long enough."""
    if hours <= 0:
        return []
    available = set(free_slots)
    runs, current = [], []
    previous_slot = None
    for index, slot in enumerate(slots):
        # These two slots touch in the list but lunch separates them in real time.
        if previous_slot == "12-1" and slot == "2-3":
            current = []
        if slot in available:
            current.append(slot)
            if len(current) >= hours:
                runs.append(current[-hours:])
        else:
            current = []
        previous_slot = slot
    # The configured slot list jumps over lunch, so windows never include it.
    return runs
