"""A moving window finds consecutive free slots without crossing long breaks."""

from config import SLOT_BREAKS

def find_windows(free_slots, slots, hours):
    """Return every run of free slots that is long enough."""
    if hours <= 0:
        return []
    available = set(free_slots)
    runs, current = [], []
    previous_slot = None
    for index, slot in enumerate(slots):
        # These periods touch in the list but a long campus break separates them.
        if (previous_slot, slot) in SLOT_BREAKS:
            current = []
        if slot in available:
            current.append(slot)
            if len(current) >= hours:
                runs.append(current[-hours:])
        else:
            current = []
        previous_slot = slot
    # The configured slot list marks long campus breaks explicitly above.
    return runs
