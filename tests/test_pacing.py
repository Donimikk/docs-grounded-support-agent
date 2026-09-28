import httpx
import pytest

from fyndit_helper.providers import MistralClient

OK = {"choices": [{"message": {"content": "answer"}}]}


@pytest.fixture
def clock(monkeypatch):
    """Replace real time, so the tests do not actually wait."""
    state = {"now": 0.0, "sleeps": []}

    def sleep(seconds: float) -> None:
        state["sleeps"].append(seconds)
        state["now"] += seconds

    monkeypatch.setattr("fyndit_helper.providers.time.sleep", sleep)
    monkeypatch.setattr("fyndit_helper.providers.time.monotonic", lambda: state["now"])
    return state


def client(clock, min_interval: float | None) -> MistralClient:
    def handler(request):
        clock["now"] += 0.1  # a call takes some time
        return httpx.Response(200, json=OK)

    return MistralClient(
        api_key="k",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        min_interval_seconds=min_interval,
    )


def test_without_spacing_nothing_waits(clock):
    c = client(clock, min_interval=None)

    for _ in range(3):
        c.complete(system_prompt="S", user_message="U")

    assert clock["sleeps"] == []


def test_the_first_call_does_not_wait(clock):
    c = client(clock, min_interval=6.0)

    c.complete(system_prompt="S", user_message="U")

    assert clock["sleeps"] == []


def test_the_following_calls_are_spaced_out(clock):
    c = client(clock, min_interval=6.0)

    for _ in range(3):
        c.complete(system_prompt="S", user_message="U")

    # Two waits between three calls, each topping up to 6s.
    assert len(clock["sleeps"]) == 2
    assert all(abs(s - 5.9) < 0.01 for s in clock["sleeps"])


def test_no_wait_when_enough_time_has_passed(clock):
    c = client(clock, min_interval=6.0)

    c.complete(system_prompt="S", user_message="U")
    clock["now"] += 30  # something took a long time in between
    c.complete(system_prompt="S", user_message="U")

    assert clock["sleeps"] == []
