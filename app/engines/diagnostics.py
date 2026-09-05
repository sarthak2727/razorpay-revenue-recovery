from typing import Tuple, Optional
from app.models.schemas import PaymentErrorDetails, FailureRootCause

class DiagnosticEngine:
    """
    Analyzes raw Razorpay payment failure codes, issuer bank telemetries,
    and metadata to classify the underlying root cause with high precision.
    """
    
    # Razorpay error code ontology mapping
    ERROR_CODE_MAP = {
        # 1. Gateway & Bank Technical Downtime
        "BAD_REQUEST_PAYMENT_TIMED_OUT": FailureRootCause.GATEWAY_OR_BANK_DOWNTIME,
        "GATEWAY_ERROR": FailureRootCause.GATEWAY_OR_BANK_DOWNTIME,
        "BAD_REQUEST_PAYMENT_FAILED_DUE_TO_BANK_ERROR": FailureRootCause.GATEWAY_OR_BANK_DOWNTIME,
        "ISSUER_BANK_DOWN": FailureRootCause.GATEWAY_OR_BANK_DOWNTIME,
        "NETWORK_TIMEOUT": FailureRootCause.GATEWAY_OR_BANK_DOWNTIME,
        "INTERNAL_SERVER_ERROR": FailureRootCause.GATEWAY_OR_BANK_DOWNTIME,
        
        # 2. Insufficient Funds / Liquidity
        "BAD_REQUEST_PAYMENT_UPI_INSUFFICIENT_FUNDS": FailureRootCause.INSUFFICIENT_FUNDS,
        "INSUFFICIENT_BALANCE": FailureRootCause.INSUFFICIENT_FUNDS,
        "DEBIT_FAILED_LOW_BALANCE": FailureRootCause.INSUFFICIENT_FUNDS,
        "MANDATE_INSUFFICIENT_FUNDS": FailureRootCause.INSUFFICIENT_FUNDS,
        
        # 3. Expired / Inactive Instrument
        "BAD_REQUEST_PAYMENT_CARD_EXPIRED": FailureRootCause.EXPIRED_INSTRUMENT,
        "CARD_INACTIVE_OR_INVALID": FailureRootCause.EXPIRED_INSTRUMENT,
        "EXPIRED_CARD": FailureRootCause.EXPIRED_INSTRUMENT,
        "ACCOUNT_CLOSED": FailureRootCause.EXPIRED_INSTRUMENT,
        
        # 4. Authentication / User Error
        "BAD_REQUEST_PAYMENT_OTP_VALIDATION_FAILED": FailureRootCause.AUTHENTICATION_FAILED,
        "BAD_REQUEST_PAYMENT_MPIN_INVALID": FailureRootCause.AUTHENTICATION_FAILED,
        "AUTH_DECLINED_BY_USER": FailureRootCause.AUTHENTICATION_FAILED,
        "INVALID_CVV": FailureRootCause.AUTHENTICATION_FAILED,
        
        # 5. Mandate & Subscriptions
        "SUBSCRIPTION_MANDATE_DECLINED": FailureRootCause.MANDATE_DEBIT_DECLINE,
        "MANDATE_LIMIT_EXCEEDED": FailureRootCause.MANDATE_DEBIT_DECLINE,
        "UPI_AUTOPAY_PRE_DEBIT_FAILED": FailureRootCause.MANDATE_DEBIT_DECLINE,
        
        # 6. Checkout Abandonment
        "PAYMENT_ABANDONED_AT_CHECKOUT": FailureRootCause.CART_ABANDONMENT,
        "USER_CLOSED_MODAL": FailureRootCause.CART_ABANDONMENT,
        "CHECKOUT_SESSION_EXPIRED": FailureRootCause.CART_ABANDONMENT,
        
        # 7. Fraud / Risk
        "RISK_SUSPECTED_FRAUD": FailureRootCause.FRAUD_RISK_FLAGGED,
        "VELOCITY_CHECK_FAILED": FailureRootCause.FRAUD_RISK_FLAGGED,
        "BLACKLISTED_CARD": FailureRootCause.FRAUD_RISK_FLAGGED,
    }

    @classmethod
    def diagnose(cls, error_details: PaymentErrorDetails, payment_method: str = "upi") -> Tuple[FailureRootCause, str]:
        code = error_details.code.upper().strip()
        
        # 1. Direct code lookup
        if code in cls.ERROR_CODE_MAP:
            root_cause = cls.ERROR_CODE_MAP[code]
            reasoning = f"Matched known Razorpay failure signature '{code}'. Classified as {root_cause.value}."
            return root_cause, reasoning
        
        # 2. Heuristic text search in description / reason
        combined_text = f"{error_details.description} {error_details.reason or ''}".lower()
        
        if any(term in combined_text for term in ["insufficient", "low balance", "funds", "limit exceeded"]):
            return FailureRootCause.INSUFFICIENT_FUNDS, "Description references liquidity/balance shortfall."
        
        if any(term in combined_text for term in ["timeout", "bank down", "gateway", "technical error", "issuer not reachable"]):
            return FailureRootCause.GATEWAY_OR_BANK_DOWNTIME, "Heuristic match for transient network/issuer failure."
        
        if any(term in combined_text for term in ["expired", "validity", "inactive card"]):
            return FailureRootCause.EXPIRED_INSTRUMENT, "Payment instrument expired or invalidated."
        
        if any(term in combined_text for term in ["otp", "mpin", "wrong pin", "auth failed", "password"]):
            return FailureRootCause.AUTHENTICATION_FAILED, "Customer entered incorrect authentication credentials (OTP/MPIN)."
            
        if any(term in combined_text for term in ["abandon", "closed", "dropped"]):
            return FailureRootCause.CART_ABANDONMENT, "Customer exited checkout before completing transaction."
        
        if any(term in combined_text for term in ["fraud", "suspicious", "risk score"]):
            return FailureRootCause.FRAUD_RISK_FLAGGED, "Transaction failed automated risk shielding."

        # Default fallback
        return FailureRootCause.UNKNOWN, f"Unrecognized error code '{code}'. Fallback diagnostic applied."
