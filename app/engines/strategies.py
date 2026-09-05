from datetime import datetime, timedelta
from typing import Tuple, Dict, Any, Optional
from app.models.schemas import RecoveryIncident, FailureRootCause, RecoveryStrategy

class StrategyPlanner:
    """
    Selects the optimal recovery workflow based on root cause, customer profile,
    amount at risk, and historical payment behaviors.
    """
    
    @classmethod
    def determine_strategy(cls, incident: RecoveryIncident) -> Tuple[RecoveryStrategy, str, Optional[datetime]]:
        root_cause = incident.root_cause
        now = datetime.utcnow()
        
        # 1. Fraud / High Risk -> Absolute Stop
        if root_cause == FailureRootCause.FRAUD_RISK_FLAGGED:
            return (
                RecoveryStrategy.COMPLIANT_TERMINATION,
                "Fraud Risk Shield tripped. No dunning or retry allowed.",
                None
            )
        
        # 2. Transient Gateway or Bank Downtime -> Silent Background Retry
        if root_cause == FailureRootCause.GATEWAY_OR_BANK_DOWNTIME:
            # Exponential backoff retry via alternate gateway rail
            backoff_minutes = 15 if incident.attempt_count == 0 else (60 * (2 ** incident.attempt_count))
            retry_time = now + timedelta(minutes=backoff_minutes)
            return (
                RecoveryStrategy.SILENT_SMART_RETRY,
                f"Transient issuer downtime detected. Silent background retry scheduled in {backoff_minutes}m (no customer disruption).",
                retry_time
            )
        
        # 3. Insufficient Funds / Liquidity Constraint -> Salary-Cycle Aligned Retry
        if root_cause in [FailureRootCause.INSUFFICIENT_FUNDS, FailureRootCause.MANDATE_DEBIT_DECLINE]:
            current_day = now.day
            paydays = incident.customer.historical_paydays or [1, 5, 7, 28, 30]
            
            # Find nearest upcoming payday
            upcoming_paydays = [d for d in paydays if d > current_day]
            target_day = upcoming_paydays[0] if upcoming_paydays else paydays[0]
            
            days_ahead = (target_day - current_day) if target_day > current_day else (30 - current_day + target_day)
            days_ahead = min(max(days_ahead, 1), 5) # Clamp to 1-5 days ahead for dunning
            
            retry_time = now + timedelta(days=days_ahead)
            return (
                RecoveryStrategy.SALARY_ALIGNED_MANDATE_RETRY,
                f"Insufficient funds classified. Mandate retry synchronized with predicted liquidity window (Day {target_day}).",
                retry_time
            )
        
        # 4. Expired Instrument -> Dynamic Update Link
        if root_cause == FailureRootCause.EXPIRED_INSTRUMENT:
            return (
                RecoveryStrategy.DYNAMIC_PAYMENT_LINK,
                "Card expired or inactive. Generating 1-click Razorpay payment link with new instrument registration.",
                now
            )
            
        # 5. Authentication Failure (OTP / MPIN drop) -> Immediate Contextual Dunning
        if root_cause == FailureRootCause.AUTHENTICATION_FAILED:
            return (
                RecoveryStrategy.CONVERSATIONAL_HINGLISH_DUNNING,
                "Customer dropped during OTP/MPIN auth. Immediate 1-click instant retry link via WhatsApp/SMS.",
                now
            )
            
        # 6. Cart Abandonment -> Intent-Preserving Gentle Engagement
        if root_cause == FailureRootCause.CART_ABANDONMENT:
            return (
                RecoveryStrategy.CONVERSATIONAL_HINGLISH_DUNNING,
                "Checkout session abandoned. Triggering conversational cart recovery with UPI 1-tap intent.",
                now + timedelta(minutes=20)
            )

        # Fallback default
        return (
            RecoveryStrategy.DYNAMIC_PAYMENT_LINK,
            "Standard recovery fallback: dispatching dynamic Razorpay payment link.",
            now
        )
