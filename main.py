from negmas.sao import SAOMechanism
from negmas.outcomes import make_issue
from negmas.preferences import LinearAdditiveUtilityFunction as LUFun
from negmas.preferences import AffineFun

from Group68_Negotiator.group_68_negotiator import Group68_Negotiator


# -------------------------
# 1. Create negotiation agenda (single issue: price)
# -------------------------
issues = [make_issue(name="price", values=50)]  # price: 0 → 49


# -------------------------
# 2. Create negotiation mechanism
# -------------------------
mechanism = SAOMechanism(issues=issues, n_steps=30)


# -------------------------
# 3. Define utility functions
# -------------------------

# Buyer prefers LOWER price
buyer_ufun = LUFun(
    values=[AffineFun(-1, 49)],   # utility = -price + 49
    weights=[1.0],
    issues=issues,
    reserved_value=34.0,
)

# Seller prefers HIGHER price
seller_ufun = LUFun(
    values=[AffineFun(1, 0)],     # utility = price
    weights=[1.0],
    issues=issues,
    reserved_value=12.0,
)


# -------------------------
# 4. Create negotiators
# -------------------------

buyer = Group68_Negotiator(name="Buyer", ufun=buyer_ufun)
seller = Group68_Negotiator(name="Seller", ufun=seller_ufun)

# Add negotiators
mechanism.add(buyer)
mechanism.add(seller)


# -------------------------
# 5. Run negotiation
# -------------------------
print("Starting negotiation...\n")

agreement = mechanism.run()


# -------------------------
# 6. Print results
# -------------------------
print("\nNegotiation finished.")

if agreement and agreement.agreement:
    final_offer = agreement.agreement
    print("Final agreed offer:", final_offer)

    print("\nUtilities:")
    print("Buyer utility:", buyer_ufun(final_offer))
    print("Seller utility:", seller_ufun(final_offer))
else:
    print("No agreement reached.")