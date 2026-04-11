import json
from unittest.mock import patch, MagicMock

import pytest

from langrobot.llm_client import parse_command


def _mock_response(text: str) -> MagicMock:
    """Build a mock requests.Response whose .json() returns Ollama's streaming format."""
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.json.return_value = {"response": text, "done": True}
    return mock


def test_valid_response():
    good_json = '{"action": "pick_and_place", "object": "red", "target": "blue"}'
    with patch("langrobot.llm_client.requests.post", return_value=_mock_response(good_json)):
        result = parse_command("move the red block onto the blue block")
    assert result == {"action": "pick_and_place", "object": "red", "target": "blue"}


def test_retry_on_bad_json():
    bad = "Sure! Here is the JSON: pick red block."
    good_json = '{"action": "pick_and_place", "object": "green", "target": "yellow"}'
    responses = [_mock_response(bad), _mock_response(good_json)]
    with patch("langrobot.llm_client.requests.post", side_effect=responses):
        result = parse_command("put green on yellow")
    assert result == {"action": "pick_and_place", "object": "green", "target": "yellow"}


def test_error_after_two_failures():
    bad = "I cannot do that."
    with patch("langrobot.llm_client.requests.post", return_value=_mock_response(bad)):
        result = parse_command("do something")
    assert result["action"] == "error"
    assert "reason" in result


def test_unknown_colour():
    bad_colour = '{"action": "pick_and_place", "object": "purple", "target": "blue"}'
    good_json = '{"action": "pick_and_place", "object": "white", "target": "blue"}'
    responses = [_mock_response(bad_colour), _mock_response(good_json)]
    with patch("langrobot.llm_client.requests.post", side_effect=responses):
        result = parse_command("move the white block to blue")
    assert result == {"action": "pick_and_place", "object": "white", "target": "blue"}


def test_ollama_unavailable():
    import requests as req
    with patch("langrobot.llm_client.requests.post", side_effect=req.ConnectionError("refused")):
        result = parse_command("move red to blue")
    assert result["action"] == "error"
    assert "reason" in result


def test_ollama_unavailable_does_not_retry():
    """Network errors short-circuit immediately — requests.post is called exactly once."""
    import requests as req
    with patch("langrobot.llm_client.requests.post", side_effect=req.ConnectionError("refused")) as mock_post:
        result = parse_command("move red to blue")
    assert result["action"] == "error"
    mock_post.assert_called_once()


def test_markdown_fenced_response():
    """LLM responses wrapped in ```json fences are correctly parsed."""
    fenced = '```json\n{"action": "pick_and_place", "object": "red", "target": "blue"}\n```'
    with patch("langrobot.llm_client.requests.post", return_value=_mock_response(fenced)):
        result = parse_command("move red to blue")
    assert result == {"action": "pick_and_place", "object": "red", "target": "blue"}


def test_same_object_and_target_is_invalid():
    bad = '{"action": "pick_and_place", "object": "red", "target": "red"}'
    good_json = '{"action": "pick_and_place", "object": "red", "target": "blue"}'
    responses = [_mock_response(bad), _mock_response(good_json)]
    with patch("langrobot.llm_client.requests.post", side_effect=responses):
        result = parse_command("move red somewhere")
    assert result == {"action": "pick_and_place", "object": "red", "target": "blue"}
