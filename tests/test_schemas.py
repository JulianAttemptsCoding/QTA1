from agorasim.schemas import DECISION_JSON_SCHEMA, AgentDecision, parse_decision


def test_limit_price_zero_coerced_to_market():
    d = parse_decision('{"action":"hold","order_type":"market","qty":0,"limit_price":0,'
                       '"confidence":0.4,"horizon_days":5,"rationale":"wait"}')
    assert d is not None and d.limit_price is None and d.order_type == "market"


def test_guided_schema_covers_all_fields_and_no_bad_keys():
    props = DECISION_JSON_SCHEMA["properties"]
    # every model field is constrainable by the guided schema
    assert set(props) == set(AgentDecision.model_fields)
    # tight rationale cap + no additionalProperties bool (see schema docstring)
    assert props["rationale"]["maxLength"] == 240
    assert "additionalProperties" not in DECISION_JSON_SCHEMA
    assert set(DECISION_JSON_SCHEMA["required"]) == set(props)


def test_valid_decision_roundtrip():
    d = parse_decision('{"action":"buy","qty":10,"confidence":0.6,"rationale":"dip"}')
    assert d is not None and d.action == "buy" and d.qty == 10 and d.order_type == "market"


def test_hold_normalizes_qty():
    d = AgentDecision(action="hold", qty=50, confidence=0.2)
    assert d.qty == 0


def test_fenced_and_prosey_output_is_parsed():
    raw = 'Sure! Here you go:\n```json\n{"action":"sell","qty":5,"confidence":0.9,"order_type":"limit","limit_price":12.5}\n```'
    d = parse_decision(raw)
    assert d is not None and d.action == "sell" and d.order_type == "limit" and d.limit_price == 12.5


def test_garbage_returns_none():
    assert parse_decision("I would probably buy some, idk") is None
    assert parse_decision('{"action":"moon","qty":1,"confidence":0.5}') is None
