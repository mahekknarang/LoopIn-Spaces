"""Greedy best fit picks the smallest suitable room to save larger ones."""
from .sorting import sort_by_capacity

def best_fit(venues, people):
    """Choose the first sorted room that has enough seats."""
    for venue in sort_by_capacity(venues):
        if venue["capacity"] >= people:
            return venue
    return None
