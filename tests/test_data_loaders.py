"""Unit tests for network-free logic in the data loaders (pagination, yielding)."""
import agorasim.data.alpaca_news as an


class _Resp:
    def __init__(self, payload):
        self._p = payload
        self.status_code = 200
        self.text = ""

    def json(self):
        return self._p

    def raise_for_status(self):
        pass


def test_iter_news_paginates(monkeypatch):
    monkeypatch.setenv("APCA_API_KEY_ID", "k")
    monkeypatch.setenv("APCA_API_SECRET_KEY", "s")
    pages = [
        {"news": [{"id": 1}, {"id": 2}], "next_page_token": "t2"},
        {"news": [{"id": 3}], "next_page_token": None},
    ]
    calls = {"i": 0}

    def fake_get(url, params=None, headers=None, timeout=None):
        resp = _Resp(pages[calls["i"]])
        calls["i"] += 1
        return resp

    monkeypatch.setattr(an.requests, "get", fake_get)
    out = list(an.iter_news(["X"], "2020-01-01", "2020-02-01"))
    assert [o["id"] for o in out] == [1, 2, 3]
    assert calls["i"] == 2


def test_iter_news_requires_keys(monkeypatch):
    monkeypatch.delenv("APCA_API_KEY_ID", raising=False)
    monkeypatch.delenv("APCA_API_SECRET_KEY", raising=False)
    try:
        list(an.iter_news(["X"], "2020-01-01", "2020-02-01"))
        assert False, "expected RuntimeError without keys"
    except RuntimeError as e:
        assert "APCA_API_KEY_ID" in str(e)
