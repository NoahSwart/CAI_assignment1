import sys
from pathlib import Path

# Allow running this file both directly and as a module.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from negmas import SAOMechanism, make_issue
from negmas.preferences import LinearAdditiveUtilityFunction as UFun

from Group68_Negotiator.bidding_strategy import BiddingStrategy


def _make_bidding_strategy() -> BiddingStrategy:
    issues = [
        make_issue(name="price", values=10),
        make_issue(name="delivery_time", values=10),
    ]
    mechanism = SAOMechanism(issues=issues, n_steps=30)
    ufun = UFun.random(issues=issues, reserved_value=(0.0, 0.2), normalized=True)
    return BiddingStrategy(mechanism, ufun)


def test_Utility():
    # check if target utility is between reserved and best, and decreases over time

    bidding = _make_bidding_strategy()

    t_grid = [0.0, 0.1, 0.3, 0.6, 0.9, 1.0]
    targets = [bidding.target_utility(t) for t in t_grid]

    reserved = float(bidding.uFun.reserved_value)
    best = float(bidding.uFun(bidding.uFun.best(bidding.nmi.outcome_space)))

    for value in targets:
        assert reserved - 1e-9 <= value <= best + 1e-9

    for i in range(1, len(targets)):
        assert targets[i] <= targets[i - 1] + 1e-9


def test_bid_usefullness():
    # check if the utility is higher or equal to target utility
    bidding = _make_bidding_strategy()

    for t in [0.0, 0.2, 0.5, 0.8, 1.0]:
        bid = bidding.get_bid(t, state=None)
        assert bid is not None

        utility = float(bidding.uFun(bid))
        target = bidding.target_utility(t)
        reserved = float(bidding.uFun.reserved_value)

        assert utility >= reserved - 1e-9
        assert utility >= target - 1e-9


if __name__ == "__main__":
    # print result 
    strategy = _make_bidding_strategy()
    print("Bidding strategy quick check")
    print("time\ttarget_u\tbid_u")
    for t in [0.0, 0.1, 0.3, 0.5, 0.8, 0.95, 1.0]:
        bid = strategy.get_bid(t, state=None)
        target_u = strategy.target_utility(t)
        bid_u = float(strategy.uFun(bid)) if bid is not None else float("nan")
        print(f"{t:.2f}\t{target_u:.4f}\t{bid_u:.4f}")