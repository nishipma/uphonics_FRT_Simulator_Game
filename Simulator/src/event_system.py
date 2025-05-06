import asyncio
from collections import defaultdict

class AsyncEventSystem:
    """An asyncio-based pub-sub event system with per-subscriber queues."""

    def __init__(self):
        # Dictionary to store event names and their associated subscriber queues
        self._events = defaultdict(list)

    def register_event(self, event_name):
        """
        Register a new event by name.
        :param event_name: The name of the event to register.
        """
        if event_name not in self._events:
            self._events[event_name] = []

    def add_listener(self, event_name):
        """
        Add a listener (queue) to an event.
        :param event_name: The name of the event to listen to.
        :return: An asyncio.Queue for the listener to consume events.
        """
        if event_name not in self._events:
            raise ValueError(f"Event '{event_name}' is not registered.")
        queue = asyncio.Queue()
        self._events[event_name].append(queue)
        return queue

    async def trigger_event(self, event_name, *args, **kwargs):
        """
        Trigger an event, putting it into all subscriber queues.
        :param event_name: The name of the event to trigger.
        :param args: Positional arguments to pass to the listeners.
        :param kwargs: Keyword arguments to pass to the listeners.
        """
        if event_name not in self._events:
            raise ValueError(f"Event '{event_name}' is not registered.")
        for queue in self._events[event_name]:
            
            await queue.put((args, kwargs))