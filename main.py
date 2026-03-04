from negmas import make_issue, SAOMechanism
from negmas.sao.negotiators import BoulwareTBNegotiator as Boulware
from negmas.sao.negotiators import LinearTBNegotiator as Linear
from negmas.preferences import LinearAdditiveUtilityFunction as UFun
from negmas.preferences.value_fun import IdentityFun
from negmas.preferences.value_fun import AffineFun


# -------------------------
# 1. Create negotiation agenda (single issue)
# -------------------------
issues = [make_issue(name="price", values=50)]  # price: 0 → 49

# -------------------------
# 2. Create negotiation mechanism
# -------------------------
mechanism = SAOMechanism(issues=issues, n_steps=20)

# -------------------------
# 3. Define utility functions
# Buyer prefers lower price
buyer_ufun = UFun(
    values=[AffineFun(-1, 49)],   # utility = -1 * price + 49
    weights=[1.0],
    issues=issues
)

# Seller prefers HIGHER price
seller_ufun = UFun(
    values=[AffineFun(1, 0)],     # utility = 1 * price + 0
    weights=[1.0],
    issues=issues
)

# -------------------------
# 4. Create negotiators
# -------------------------
buyer = Linear(name="Buyer", ufun=buyer_ufun)
seller = Boulware(name="Seller", ufun=seller_ufun)

# Add negotiators to mechanism
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
# print("Agreement:", agreement)

if agreement and agreement.agreement:
    final_offer = agreement.agreement
    print("Final agreed offer:", final_offer)
    print("Buyer utility:", buyer_ufun(final_offer))
    print("Seller utility:", seller_ufun(final_offer))
else:
    print("No agreement reached.")

# print("\nNegotiation trace:")
# for step in mechanism.history:
#     print(step)