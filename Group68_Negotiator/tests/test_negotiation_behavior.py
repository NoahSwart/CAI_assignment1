import sys
from pathlib import Path

# Allow running this file both directly and as a module.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from negmas.outcomes import make_issue
from negmas.preferences import LinearAdditiveUtilityFunction as LUFun
from negmas.preferences import AffineFun
from negmas.sao import SAOMechanism, ToughNegotiator

from Group68_Negotiator.group_68_negotiator import Group68_Negotiator


def test_overlap_domain_self_play_reaches_agreement():
    issues = [make_issue(name="price", values=50)]
    mechanism = SAOMechanism(issues=issues, n_steps=30)

    buyer_ufun = LUFun(
        values=[AffineFun(-1, 49)],
        weights=[1.0],
        issues=issues,
        reserved_value=34.0,
    )
    seller_ufun = LUFun(
        values=[AffineFun(1, 0)],
        weights=[1.0],
        issues=issues,
        reserved_value=12.0,
    )

    mechanism.add(Group68_Negotiator(name="Buyer", ufun=buyer_ufun))
    mechanism.add(Group68_Negotiator(name="Seller", ufun=seller_ufun))

    result = mechanism.run()

    assert result is not None
    assert result.agreement is not None


def test_accepts_reservation_level_offer_against_tough_negotiator():
    issues = [make_issue(name="price", values=10)]
    mechanism = SAOMechanism(issues=issues, n_steps=20)

    buyer_ufun = LUFun(
        values=[AffineFun(-1, 9)],
        weights=[1.0],
        issues=issues,
        reserved_value=0.0,
    )
    seller_ufun = LUFun(
        values=[AffineFun(1, 0)],
        weights=[1.0],
        issues=issues,
        reserved_value=0.0,
    )

    mechanism.add(Group68_Negotiator(name="Buyer", ufun=buyer_ufun))
    mechanism.add(ToughNegotiator(name="ToughSeller", ufun=seller_ufun))

    result = mechanism.run()

    assert result is not None
    assert result.agreement is not None
