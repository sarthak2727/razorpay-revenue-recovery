from typing import Dict, Any, List
from app.models.schemas import RecoveryIncident

class PaymentInstrumentOptimizer:
    """
    Dynamic Payment Instrument Downgrade & Split-Payment Planner.
    Generates intelligent alternative checkout configurations when primary payment rail fails:
    - 1-Click UPI Intent Link
    - Split 2-Part Flexible Settlement
    - No-Cost EMI / PayLater Conversion
    - Alternate Issuer Bank / UPI Lite Switch
    """

    @classmethod
    def get_alternative_payment_options(cls, incident: RecoveryIncident) -> Dict[str, Any]:
        amount = incident.amount_inr
        split_50 = round(amount / 2.0, 2)
        emi_3m = round(amount / 3.0, 2)

        options = [
            {
                "id": "full_upi",
                "label": "Instant 1-Click UPI Intent",
                "badge": "FASTEST",
                "description": "One-tap direct approval on GPay / PhonePe / Paytm",
                "amount_inr": amount,
                "terms": "Instant single settlement",
                "recommended": True
            },
            {
                "id": "split_2part",
                "label": "2-Part Flexible Split Settlement",
                "badge": "ZERO_INTEREST",
                "description": f"Pay ₹{split_50:,.2f} today, balance ₹{split_50:,.2f} in 7 days",
                "amount_inr": split_50,
                "terms": "2 x Equal installments without late fee",
                "recommended": amount >= 2000
            },
            {
                "id": "nocost_emi",
                "label": "3-Month No-Cost EMI",
                "badge": "AFFORDABLE",
                "description": f"₹{emi_3m:,.2f}/month across 3 months via Credit/Debit card",
                "amount_inr": emi_3m,
                "terms": "Powered by Razorpay Instant EMI",
                "recommended": amount >= 3000
            }
        ]

        return {
            "incident_id": incident.incident_id,
            "original_amount_inr": amount,
            "failed_method": incident.payment_method,
            "alternative_options": options
        }
