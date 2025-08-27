# adapters/io_if.py — 目/耳/手足の差し口（薄いIF）
from typing import Protocol, Dict, Any

class Sensor(Protocol):
    def pull(self) -> Dict[str, Any]: ...

class EventSensor(Protocol):
    def push(self, event: Dict[str, Any]) -> None: ...

class Actuator(Protocol):
    def act(self, **kw) -> Dict[str, Any]: ...

class AdapterRegistry:
    def __init__(self):
        self._sensors = {}; self._events = {}; self._acts = {}
    def register_sensor(self, name: str, s: Sensor): self._sensors[name]=s
    def register_event(self, name: str, e: EventSensor): self._events[name]=e
    def register_actuator(self, name: str, a: Actuator): self._acts[name]=a
    def sensor(self, name): return self._sensors[name]
    def event(self, name): return self._events[name]
    def actuator(self, name): return self._acts[name]

