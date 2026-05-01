from collections import deque
from dataclasses import dataclass
from typing import Any
import time

@dataclass
class DelayedEvent:
    event: Any          # your Event instance
    delta: float        # additional seconds beyond the previous entry

class DeltaQueue:
    def __init__(self):
        self._queue: deque[DelayedEvent] = deque()
        self._interval_start: float | None = None   # when current monitored interval began
        self._interval_duration: float = 0.0        # how long the current interval runs

    @property
    def monitoring(self) -> bool:
        return self._interval_start is not None

    @property
    def remaining(self) -> float:
        """Seconds left on the current monitored interval."""
        if not self.monitoring:
            return 0.0
        return max(0.0, self._interval_duration - (time.monotonic() - self._interval_start))

    def enqueue(self, event: Any, delay: float) -> None:
        """Add an event to fire after `delay` seconds from now."""
        if not self._queue:
            # Queue is empty — start monitoring this interval directly
            self._queue.append(DelayedEvent(event=event, delta=0.0))
            self._interval_start = time.monotonic()
            self._interval_duration = delay
            return

        r = self.remaining
        tail_accumulation = 0.0
        insert_at = len(self._queue)

        # Walk the queue accumulating deltas to find insertion point
        for i, entry in enumerate(self._queue):
            tail_accumulation += entry.delta
            absolute_at = r + tail_accumulation   # time from now when entry i fires
            if delay < absolute_at:
                insert_at = i
                break

        if insert_at == 0:
            # Goes before the current head — becomes the new monitored interval
            old_remaining = r
            new_delta_for_old_head = old_remaining - delay
            # Restart the monitored interval
            self._interval_start = time.monotonic()
            self._interval_duration = delay
            # Head entry keeps delta=0; bump the old head's successor delta
            self._queue[0] = DelayedEvent(event=self._queue[0].event, delta=new_delta_for_old_head)
            self._queue.appendleft(DelayedEvent(event=event, delta=0.0))
        else:
            # Insert in the interior or at the tail
            predecessor_absolute = r + sum(e.delta for e in list(self._queue)[:insert_at])
            new_delta = delay - predecessor_absolute
            entry = DelayedEvent(event=event, delta=new_delta)
            if insert_at < len(self._queue):
                # Reduce the successor's delta by our new_delta
                successor = self._queue[insert_at]
                self._queue[insert_at] = DelayedEvent(
                    event=successor.event,
                    delta=successor.delta - new_delta
                )
            self._queue.insert(insert_at, entry)

    def check(self) -> list[Any]:
        """
        Call periodically. Returns a list of events whose intervals have expired,
        in order. Resets the monitor to the next entry's interval if one exists.
        """
        if not self.monitoring or self.remaining > 0:
            return []

        dispatched = []

        # Dispatch the head
        head = self._queue.popleft()
        dispatched.append(head.event)

        # Dispatch any subsequent entries with delta=0 (co-scheduled)
        while self._queue and self._queue[0].delta == 0:
            dispatched.append(self._queue.popleft().event)

        # Arm the next interval if anything remains
        if self._queue:
            next_entry = self._queue[0]
            self._interval_start = time.monotonic()
            self._interval_duration = next_entry.delta
        else:
            self._interval_start = None
            self._interval_duration = 0.0

        return dispatched
