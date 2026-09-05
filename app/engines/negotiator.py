from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from app.models.schemas import RecoveryIncident, RecoveryStatus
from app.core.state_machine import RecoveryStateMachine

class AutonomousNegotiator:
    """
    Autonomous Objection Handling & Dynamic Grace-Period Negotiator.
    Evaluates customer replies and objections with bounded merchant policies:
    - Low balance / cash crunch -> Grants 3-day grace period hold with auto-pause.
    - Discount request -> Authorizes bounded 5-10% instant settlement discount for high-intent/LTV.
    - Subscription cancel intent -> Executes smart retention offer / plan downgrade before opt-out.
    - Postponement ("kal karunga", "next week") -> Schedules calendar-aligned notification.
    """

    @classmethod
    def handle_objection(cls, incident: RecoveryIncident, customer_text: str) -> Dict[str, Any]:
        text = customer_text.lower().strip()
        cust_name = incident.customer.name.split()[0]
        amount = incident.amount_inr

        # 1. Immediate Opt-Out
        if any(w in text for w in ["stop", "dnd", "unsubscribe", "mat bhejo", "block"]):
            RecoveryStateMachine.transition(
                incident=incident,
                new_status=RecoveryStatus.OPTED_OUT,
                action_name="OPT_OUT_HONORED",
                reason="Customer requested communication halt via keyword.",
                rule_or_model="AutonomousNegotiator"
            )
            return {
                "action": "OPTED_OUT",
                "policy_applied": "IMMEDIATE_DND",
                "response_message": f"Understood {cust_name}. We have stopped all reminders for this transaction. No further messages will be sent.",
                "adjusted_amount_inr": amount,
                "grace_period_days": 0
            }

        # 2. Discount / Bargaining Request
        if any(w in text for w in ["discount", "kam karo", "offer", "coupon", "kam karo na", "cheaper"]):
            discount_pct = 10 if amount >= 2000 else 5
            discounted_amt = round(amount * (1.0 - (discount_pct / 100.0)), 2)
            
            RecoveryStateMachine.transition(
                incident=incident,
                new_status=RecoveryStatus.ENGAGED,
                action_name="AUTHORIZED_SETTLEMENT_DISCOUNT",
                reason=f"Authorized {discount_pct}% instant settlement discount under merchant retention policy.",
                rule_or_model="AutonomousNegotiator",
                metadata={"original_amount": amount, "discounted_amount": discounted_amt, "discount_pct": discount_pct}
            )
            return {
                "action": "DISCOUNT_OFFERED",
                "policy_applied": f"INSTANT_{discount_pct}PCT_SETTLEMENT_TOKEN",
                "discount_percentage": discount_pct,
                "adjusted_amount_inr": discounted_amt,
                "grace_period_days": 0,
                "response_message": (
                    f"Namaste {cust_name}! We understand. As a valued customer, we've applied a special {discount_pct}% instant settlement discount. "
                    f"Your new payable amount is ₹{discounted_amt:,.2f} (saved ₹{round(amount - discounted_amt, 2):,.2f}). "
                    f"Pay here: https://rzp.io/i/disc_{incident.incident_id[-6:]}"
                )
            }

        # 3. Liquidity Crunch / "Paise nahi hai" -> Grace Period Offer
        if any(w in text for w in ["paise nahi", "no money", "paisa nahi", "salary nahi aayi", "balance nahi hai", "fund problem"]):
            grace_days = 3
            rescheduled_date = (datetime.utcnow() + timedelta(days=grace_days)).strftime("%Y-%m-%d 10:30 IST")
            
            RecoveryStateMachine.transition(
                incident=incident,
                new_status=RecoveryStatus.COOLING_OFF,
                action_name="GRANT_GRACE_PERIOD",
                reason=f"Granted {grace_days}-day grace period on liquidity shortfall objection.",
                rule_or_model="AutonomousNegotiator",
                metadata={"grace_period_days": grace_days, "rescheduled_date": rescheduled_date}
            )
            return {
                "action": "GRACE_PERIOD_GRANTED",
                "policy_applied": "3_DAY_AUTOPAUSE_HOLD",
                "grace_period_days": grace_days,
                "adjusted_amount_inr": amount,
                "rescheduled_date": rescheduled_date,
                "response_message": (
                    f"Koi baat nahi {cust_name} ji! We've granted a {grace_days}-day grace period. "
                    f"Your service will remain active until {rescheduled_date}. We will gently remind you then!"
                )
            }

        # 4. Cancellation / Churn Threat -> Smart Retention Flow
        if any(w in text for w in ["cancel", "nahi chahiye", "close", "band kardo", "terminate"]):
            RecoveryStateMachine.transition(
                incident=incident,
                new_status=RecoveryStatus.ENGAGED,
                action_name="RETENTION_OFFER_PRESENTED",
                reason="Presented 50% lite downgrade plan before final cancellation.",
                rule_or_model="AutonomousNegotiator",
                metadata={"retention_plan": "LITE_TIER_50PCT"}
            )
            lite_amt = round(amount * 0.5, 2)
            return {
                "action": "RETENTION_DOWNGRADE_OFFERED",
                "policy_applied": "PLAN_DOWNGRADE_PRESERVATION",
                "adjusted_amount_inr": lite_amt,
                "grace_period_days": 0,
                "response_message": (
                    f"We'd hate to see you go {cust_name}! Would you prefer switching to our Lite Tier at just ₹{lite_amt:,.2f}/month (50% off) "
                    f"instead of full cancellation? Reply 'YES' to switch, or 'CANCEL' to confirm closing."
                )
            }

        # 5. Delay / Postponement ("kal karta hu", "next week", "later")
        if any(w in text for w in ["kal", "tomorrow", "later", "baad me", "evening", "shaam", "next week"]):
            rescheduled_date = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d 11:00 IST")
            RecoveryStateMachine.transition(
                incident=incident,
                new_status=RecoveryStatus.ENGAGED,
                action_name="RESCHEDULE_ACKNOWLEDGED",
                reason="Customer requested reminder postponement.",
                rule_or_model="AutonomousNegotiator",
                metadata={"rescheduled_date": rescheduled_date}
            )
            return {
                "action": "RESCHEDULED",
                "policy_applied": "CUSTOMER_PREFERRED_WINDOW",
                "adjusted_amount_inr": amount,
                "grace_period_days": 1,
                "response_message": f"Sure {cust_name}! We have paused notifications and scheduled a reminder for tomorrow ({rescheduled_date}). Have a great day!"
            }

        # Default fallback
        return {
            "action": "INFO_PROVIDED",
            "policy_applied": "STANDARD_CLARIFICATION",
            "adjusted_amount_inr": amount,
            "grace_period_days": 0,
            "response_message": f"Namaste {cust_name}. Your secure Razorpay payment link for ₹{amount:,.2f} is active: https://rzp.io/i/{incident.incident_id[-6:]}. Let us know if you need assistance!"
        }
