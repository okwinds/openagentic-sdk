from __future__ import annotations


class OpenAgentSdkError(Exception):
    pass


class InvalidEventError(OpenAgentSdkError, ValueError):
    pass


class UnknownEventTypeError(InvalidEventError):
    def __init__(self, event_type: str) -> None:
        super().__init__(f"unknown event type: {event_type}")
        self.event_type = event_type

