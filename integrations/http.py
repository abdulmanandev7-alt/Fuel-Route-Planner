from contextvars import ContextVar

import requests

_external_calls: ContextVar[int] = ContextVar("external_calls", default=0)


def build_session(user_agent: str) -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = user_agent
    return session


def record_external_call() -> None:
    _external_calls.set(_external_calls.get() + 1)


def reset_external_calls() -> None:
    _external_calls.set(0)


def external_calls_made() -> int:
    return _external_calls.get()
