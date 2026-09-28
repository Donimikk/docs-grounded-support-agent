import pytest

from fyndit_helper.llm import LLMError, RecordingClient, ScriptedClient


# --- ScriptedClient (the double for the multi-step flow) -------------------


def test_scripted_client_returns_answers_in_order():
    client = ScriptedClient(["first", "second"])

    assert client.complete(system_prompt="S1", user_message="U1") == "first"
    assert client.complete(system_prompt="S2", user_message="U2") == "second"
    assert client.calls == [("S1", "U1"), ("S2", "U2")]


def test_scripted_client_reports_when_it_runs_out_of_answers():
    client = ScriptedClient(["only one"])
    client.complete(system_prompt="S", user_message="U")

    with pytest.raises(LLMError, match="more calls"):
        client.complete(system_prompt="S", user_message="U")


# --- RecordingClient (test double) -----------------------------------------


def test_recording_client_records_what_it_received():
    client = RecordingClient(reply="answer")

    result = client.complete(system_prompt="SYSTEM", user_message="USER")

    assert result == "answer"
    assert client.last_system_prompt == "SYSTEM"
    assert client.last_user_message == "USER"


def test_recording_client_can_simulate_a_failure():
    client = RecordingClient(reply="x", fail_with=LLMError("provider unavailable"))

    with pytest.raises(LLMError, match="unavailable"):
        client.complete(system_prompt="S", user_message="U")
