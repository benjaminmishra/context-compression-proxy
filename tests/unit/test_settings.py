import pytest
from proxy.settings import Settings


def test_user_tokens_parses_mapping(monkeypatch):
    monkeypatch.setenv("CCP_USER_TOKENS", "tok1:alice, tok2:bob")
    settings = Settings()
    assert settings.user_tokens == {"tok1": "alice", "tok2": "bob"}


def test_user_tokens_empty_when_unset(monkeypatch):
    monkeypatch.delenv("CCP_USER_TOKENS", raising=False)
    settings = Settings()
    assert settings.user_tokens == {}


def test_user_tokens_invalid_pair_raises(monkeypatch):
    monkeypatch.setenv("CCP_USER_TOKENS", "missingcolon")
    with pytest.raises(ValueError):
        Settings().user_tokens
