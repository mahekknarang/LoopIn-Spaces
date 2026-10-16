"""Merge sort keeps the same clear ordering for rooms, slots, and history."""

def merge_sort(items, key):
    """Sort a copy with merge sort so the original list stays unchanged."""
    if len(items) < 2:
        return list(items)
    middle = len(items) // 2
    left = merge_sort(items[:middle], key)
    right = merge_sort(items[middle:], key)
    result, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        if key(left[i]) <= key(right[j]):
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    return result + left[i:] + right[j:]

def sort_by_capacity(items):
    """Put the smallest suitable room first for the best-fit search."""
    return merge_sort(items, lambda item: item["capacity"])

def sort_slots(slots, all_slots):
    """Keep time slots in the one order chosen in config.py."""
    order = {slot: index for index, slot in enumerate(all_slots)}
    return merge_sort(slots, lambda slot: order.get(slot, len(order)))

def sort_history(items):
    """Put the newest decided request first in the history tab."""
    return merge_sort(items, lambda item: item.get("created_at", ""))[::-1]

def slot_order(slot, slots):
    """Return a slot's position, or the end if it is unknown."""
    return slots.index(slot) if slot in slots else len(slots)
