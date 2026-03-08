from negmas import SAONegotiator, ResponseType, SAOState
from negmas.outcomes import Outcome
from typing import Optional



class Group68_Negotiator(SAONegotiator):

    # Initialize all of the sub components, like bidding strategy, acceptance strategy, opponent model, etc...
    # Reset any stateful variables to prepare for a new negotiation.
    def negotiation_start(self, state: SAOState) -> None:
        pass

    # Return the nexxt offer to send to the opponent, which we call when we need to make a bid.
    def propose(self, state: SAOState) -> Optional[Outcome]:
        pass
    
    # Here we decide whether to accept offer, reject it or end the negotiation, which we call when the opponent makes an offer.
    def respond(self, state: SAOState, offer: Outcome) -> ResponseType:
        pass