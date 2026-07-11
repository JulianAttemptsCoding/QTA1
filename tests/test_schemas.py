from agorasim.schemas import AgentDecision, parse_decision


def test_valid_decision_roundtrip():
    d = parse_decision('{"action":"buy","qty":10,"confidence":0.6,"rationale":"dip"}')
    assert d is not None and d.action == "buy" and d.qty == 10 and d.order_type == "market"


def test_hold_normalizes_qty():
    d = AgentDecision(action="hold", qty=50, confidence=0.2)
    assert d.qty == 0


def test_market_order_ignores_zero_limit_price():
    d = parse_decision('{"action":"buy","order_type":"market","qty":10,"limit_price":0,"confidence":0.6}')
    assert d is not None and d.order_type == "market" and d.limit_price is None


def test_zero_limit_order_falls_back_to_market():
    d = parse_decision('{"action":"sell","order_type":"limit","qty":10,"limit_price":0,"confidence":0.6}')
    assert d is not None and d.order_type == "market" and d.limit_price is None


def test_fenced_and_prosey_output_is_parsed():
    raw = 'Sure! Here you go:\n```json\n{"action":"sell","qty":5,"confidence":0.9,"order_type":"limit","limit_price":12.5}\n```'
    d = parse_decision(raw)
    assert d is not None and d.action == "sell" and d.order_type == "limit" and d.limit_price == 12.5


def test_garbage_returns_none():
    assert parse_decision("I would probably buy some, idk") is None
    assert parse_decision('{"action":"moon","qty":1,"confidence":0.5}') is None
