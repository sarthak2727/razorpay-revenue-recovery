from typing import Dict, Any, Optional
from app.models.schemas import RecoveryIncident, FailureRootCause, RecoveryStrategy
from app.integrations.razorpay_client import razorpay_client

class RecoveryAgent:
    """
    Autonomous Multi-Channel Engagement Agent.
    Crafts empathetic, localized (English & Hinglish) dunning messages
    with embedded 1-click Razorpay payment links and compliance footer.
    """

    @classmethod
    def generate_outreach_message(cls, incident: RecoveryIncident) -> Dict[str, Any]:
        """
        Generates channel-specific message payload based on customer language and root cause.
        """
        cust_name = incident.customer.name.split()[0]
        amount_str = f"₹{incident.amount_inr:,.2f}"
        lang = incident.customer.preferred_language
        
        # Ensure a Razorpay payment link exists
        if not incident.generated_payment_link:
            link_data = razorpay_client.create_payment_link(
                amount_inr=incident.amount_inr,
                customer_name=incident.customer.name,
                customer_email=incident.customer.email,
                customer_phone=incident.customer.phone,
                description=f"Payment for {incident.merchant_id} (Ref: {incident.incident_id})",
                reference_id=incident.incident_id
            )
            incident.generated_payment_link = link_data["short_url"]
            
        link = incident.generated_payment_link
        
        # English / Hinglish Templates
        if lang in ["hi", "hinglish"]:
            if incident.root_cause == FailureRootCause.AUTHENTICATION_FAILED:
                text = (
                    f"Hi {cust_name}! 👋 Aapka {amount_str} ka payment bank authorization timeout ki wajah se complete nahi ho paya. "
                    f"Aap yahan se bina kisi hassle ke 1-tap me complete kar sakte hain: {link}\n\n"
                    f"Agar koi issue ho toh hume reply karein. (Opt-out karne ke liye STOP bhejein)"
                )
            elif incident.root_cause == FailureRootCause.EXPIRED_INSTRUMENT:
                text = (
                    f"Hi {cust_name}, aapka card expire hone ke karan subscription renew nahi ho saki. "
                    f"Naya payment method update karne ke liye yahan click karein: {link}\n\n"
                    f"Reply STOP to unsubscribe."
                )
            elif incident.root_cause == FailureRootCause.CART_ABANDONMENT:
                text = (
                    f"Hi {cust_name}! Aapka cart wait kar raha hai. {amount_str} ka payment complete karke instant dispatch payein: {link}\n\n"
                    f"Reply STOP to opt out."
                )
            else:
                text = (
                    f"Namaste {cust_name}! {amount_str} ka pending transaction complete karne ke liye direct Razorpay secure link: {link}\n\n"
                    f"Reply STOP to unsubscribe."
                )
        else: # Standard English
            if incident.root_cause == FailureRootCause.AUTHENTICATION_FAILED:
                text = (
                    f"Hi {cust_name}, your payment of {amount_str} could not be completed due to a temporary authentication timeout. "
                    f"You can quickly retry and complete it here via secure 1-click Razorpay checkout: {link}\n\n"
                    f"Reply STOP to unsubscribe from payment reminders."
                )
            elif incident.root_cause == FailureRootCause.EXPIRED_INSTRUMENT:
                text = (
                    f"Hi {cust_name}, your recurring payment of {amount_str} failed because the payment method on file has expired. "
                    f"Please update your details and complete payment here: {link}\n\n"
                    f"Reply STOP to unsubscribe."
                )
            elif incident.root_cause == FailureRootCause.CART_ABANDONMENT:
                text = (
                    f"Hi {cust_name}, you left items in your cart ({amount_str}). "
                    f"Complete your order in 1-click here: {link}\n\n"
                    f"Reply STOP to opt-out."
                )
            else:
                text = (
                    f"Hi {cust_name}, your transaction of {amount_str} is pending. "
                    f"Click here to complete payment safely: {link}\n\n"
                    f"Reply STOP to unsubscribe."
                )

        return {
            "channel": "WHATSAPP",
            "recipient": incident.customer.phone or incident.customer.email,
            "language": lang,
            "message_body": text,
            "payment_link": link,
            "attempt_number": incident.attempt_count + 1
        }

    @classmethod
    def handle_customer_reply(cls, incident: RecoveryIncident, customer_reply_text: str) -> Dict[str, Any]:
        """
        Handles incoming customer responses (e.g. STOP, promise to pay, objection, queries).
        """
        reply_lower = customer_reply_text.lower().strip()
        
        # 1. Opt-out intent
        if any(w in reply_lower for w in ["stop", "unsubscribe", "band karo", "roko", "dont message"]):
            incident.is_opted_out = True
            return {
                "action": "OPT_OUT",
                "response_message": "You have been successfully unsubscribed. No further recovery reminders will be sent."
            }
            
        # 2. Promise to pay later
        if any(w in reply_lower for w in ["tomorrow", "kal", "next week", "later", "salary", "baad me"]):
            return {
                "action": "RESCHEDULE",
                "response_message": "Got it! We have paused reminders and will keep your payment link active for 48 hours. Thank you!"
            }
            
        # 3. Discount request
        if any(w in reply_lower for w in ["discount", "offer", "kam karo", "coupon"]):
            return {
                "action": "OFFER_DISCOUNT",
                "response_message": "Here is a 5% instant recovery coupon: 'RECOVR5'. Use it on your checkout link to complete the payment!"
            }

        # Default helpful assistant reply
        return {
            "action": "ASSIST",
            "response_message": f"Sure! You can complete your transaction securely anytime using this Razorpay link: {incident.generated_payment_link}"
        }
