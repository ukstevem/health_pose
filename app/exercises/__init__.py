from .squat import SquatTracker

# Registry of available exercises. Add new trackers here as Circuit A grows
# (push-ups, glute bridges, inverted rows, dead bug, plank).
TRACKERS = {
    "squat": SquatTracker,
}


def make_tracker(name: str):
    name = (name or "squat").lower()
    cls = TRACKERS.get(name)
    if cls is None:
        raise ValueError(f"unknown exercise '{name}'; have {list(TRACKERS)}")
    return cls()
