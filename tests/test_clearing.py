from agorasim.market import call_auction, flow_imbalance
from agorasim.schemas import AgentDecision


def D(**kw):
    base = dict(action="hold", qty=0, confidence=0.5)
    base.update(kw)
    return AgentDecision(**base)


def test_imbalance_signs_and_bounds():
    ds = [D(action="buy", qty=100, confidence=1.0), D(action="sell", qty=50, confidence=1.0)]
    ib = flow_imbalance(ds)
    assert 0 < ib <= 1 and abs(ib - (50 / 150)) < 1e-9
    assert flow_imbalance([D()]) == 0.0


def test_auction_crosses_at_volume_maximizing_price():
    ds = [
        D(action="buy", order_type="limit", qty=100, limit_price=10.10, confidence=0.8),
        D(action="buy", order_type="market", qty=50, confidence=0.9),
        D(action="sell", order_type="limit", qty=120, limit_price=10.00, confidence=0.7),
    ]
    res = call_auction(ds, last_price=10.05)
    assert res.volume == 120
    assert 10.00 <= res.price <= 10.10


def test_auction_no_cross_returns_last_price():
    ds = [
        D(action="buy", order_type="limit", qty=10, limit_price=9.00, confidence=0.5),
        D(action="sell", order_type="limit", qty=10, limit_price=11.00, confidence=0.5),
    ]
    res = call_auction(ds, last_price=10.00)
    assert res.volume == 0 and res.price == 10.00
