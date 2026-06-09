from unittest.mock import MagicMock, patch
from core.llm import is_configured, check_api_key, UsageTracker


# ─── is_configured ────────────────────────────────────────────────────────────

def test_is_configured_false_when_no_env(monkeypatch):
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
    assert is_configured("cerebras") is False


def test_is_configured_true_when_env_set(monkeypatch):
    monkeypatch.setenv("CEREBRAS_API_KEY", "test-key")
    assert is_configured("cerebras") is True


def test_is_configured_false_for_empty_string(monkeypatch):
    monkeypatch.setenv("CEREBRAS_API_KEY", "")
    assert is_configured("cerebras") is False


def test_is_configured_openai(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert is_configured("openai") is True


# ─── check_api_key: no key ────────────────────────────────────────────────────

def test_check_api_key_no_key_returns_no_key_status(monkeypatch):
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
    result = check_api_key("cerebras")
    assert result["status"] == "no_key"
    assert "checked_at" in result
    assert "message" in result


# ─── check_api_key: active ────────────────────────────────────────────────────

@patch("core.llm.ChatOpenAI")
def test_check_api_key_active(mock_chat, monkeypatch):
    monkeypatch.setenv("CEREBRAS_API_KEY", "valid-key")
    mock_model = MagicMock()
    mock_model.invoke.return_value = MagicMock()
    mock_chat.return_value = mock_model
    result = check_api_key("cerebras")
    assert result["status"] == "active"
    assert result["checked_at"] is not None


# ─── check_api_key: error classification ─────────────────────────────────────

@patch("core.llm.ChatOpenAI")
def test_check_api_key_invalid_key(mock_chat, monkeypatch):
    monkeypatch.setenv("CEREBRAS_API_KEY", "bad-key")
    mock_model = MagicMock()
    mock_model.invoke.side_effect = Exception("401 invalid api key")
    mock_chat.return_value = mock_model
    result = check_api_key("cerebras")
    assert result["status"] == "invalid_key"


@patch("core.llm.ChatOpenAI")
def test_check_api_key_authentication_error(mock_chat, monkeypatch):
    monkeypatch.setenv("CEREBRAS_API_KEY", "bad-key")
    mock_model = MagicMock()
    mock_model.invoke.side_effect = Exception("Authentication failed: incorrect api key")
    mock_chat.return_value = mock_model
    result = check_api_key("cerebras")
    assert result["status"] == "invalid_key"


@patch("core.llm.ChatOpenAI")
def test_check_api_key_quota_exceeded(mock_chat, monkeypatch):
    monkeypatch.setenv("CEREBRAS_API_KEY", "some-key")
    mock_model = MagicMock()
    mock_model.invoke.side_effect = Exception("429 rate limit exceeded quota")
    mock_chat.return_value = mock_model
    result = check_api_key("cerebras")
    assert result["status"] == "no_credits"


@patch("core.llm.ChatOpenAI")
def test_check_api_key_billing_error(mock_chat, monkeypatch):
    monkeypatch.setenv("CEREBRAS_API_KEY", "some-key")
    mock_model = MagicMock()
    mock_model.invoke.side_effect = Exception("insufficient_quota billing issue")
    mock_chat.return_value = mock_model
    result = check_api_key("cerebras")
    assert result["status"] == "no_credits"


@patch("core.llm.ChatOpenAI")
def test_check_api_key_unknown_error(mock_chat, monkeypatch):
    monkeypatch.setenv("CEREBRAS_API_KEY", "some-key")
    mock_model = MagicMock()
    mock_model.invoke.side_effect = Exception("Connection timeout")
    mock_chat.return_value = mock_model
    result = check_api_key("cerebras")
    assert result["status"] == "error"
    assert "Connection timeout" in result["message"]


# ─── UsageTracker ─────────────────────────────────────────────────────────────

def test_usage_tracker_starts_at_zero():
    tracker = UsageTracker()
    assert tracker.total_tokens == 0


def test_usage_tracker_accumulates_tokens():
    tracker = UsageTracker()
    gen = MagicMock()
    gen.message.usage_metadata = {"total_tokens": 42}
    response = MagicMock()
    response.generations = [[gen]]
    tracker.on_llm_end(response)
    assert tracker.total_tokens == 42


def test_usage_tracker_accumulates_across_multiple_calls():
    tracker = UsageTracker()

    def _resp(n):
        gen = MagicMock()
        gen.message.usage_metadata = {"total_tokens": n}
        r = MagicMock()
        r.generations = [[gen]]
        return r

    tracker.on_llm_end(_resp(30))
    tracker.on_llm_end(_resp(20))
    assert tracker.total_tokens == 50


def test_usage_tracker_handles_multiple_generations_per_call():
    tracker = UsageTracker()
    gen1 = MagicMock()
    gen1.message.usage_metadata = {"total_tokens": 10}
    gen2 = MagicMock()
    gen2.message.usage_metadata = {"total_tokens": 15}
    response = MagicMock()
    response.generations = [[gen1], [gen2]]
    tracker.on_llm_end(response)
    assert tracker.total_tokens == 25


def test_usage_tracker_handles_missing_message_attribute():
    tracker = UsageTracker()
    gen = MagicMock(spec=[])  # no 'message' attribute
    response = MagicMock()
    response.generations = [[gen]]
    tracker.on_llm_end(response)  # must not raise
    assert tracker.total_tokens == 0


def test_usage_tracker_handles_none_usage_metadata():
    tracker = UsageTracker()
    gen = MagicMock()
    gen.message.usage_metadata = None
    response = MagicMock()
    response.generations = [[gen]]
    tracker.on_llm_end(response)
    assert tracker.total_tokens == 0
