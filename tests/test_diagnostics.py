import pytest
from app.models.schemas import PaymentErrorDetails, FailureRootCause
from app.engines.diagnostics import DiagnosticEngine

def test_diagnose_known_error_codes():
    err1 = PaymentErrorDetails(code="BAD_REQUEST_PAYMENT_OTP_VALIDATION_FAILED", description="OTP failed")
    cause, _ = DiagnosticEngine.diagnose(err1)
    assert cause == FailureRootCause.AUTHENTICATION_FAILED

    err2 = PaymentErrorDetails(code="GATEWAY_ERROR", description="Timeout on bank switch")
    cause, _ = DiagnosticEngine.diagnose(err2)
    assert cause == FailureRootCause.GATEWAY_OR_BANK_DOWNTIME

    err3 = PaymentErrorDetails(code="BAD_REQUEST_PAYMENT_UPI_INSUFFICIENT_FUNDS", description="No balance")
    cause, _ = DiagnosticEngine.diagnose(err3)
    assert cause == FailureRootCause.INSUFFICIENT_FUNDS

    err4 = PaymentErrorDetails(code="BAD_REQUEST_PAYMENT_CARD_EXPIRED", description="Expired card")
    cause, _ = DiagnosticEngine.diagnose(err4)
    assert cause == FailureRootCause.EXPIRED_INSTRUMENT

    err5 = PaymentErrorDetails(code="RISK_SUSPECTED_FRAUD", description="Blacklisted IP")
    cause, _ = DiagnosticEngine.diagnose(err5)
    assert cause == FailureRootCause.FRAUD_RISK_FLAGGED

def test_diagnose_text_heuristics():
    err = PaymentErrorDetails(code="CUSTOM_UNKNOWN_CODE", description="Customer account has low balance")
    cause, _ = DiagnosticEngine.diagnose(err)
    assert cause == FailureRootCause.INSUFFICIENT_FUNDS

    err_timeout = PaymentErrorDetails(code="CUSTOM_TIMEOUT", description="Issuer bank down during debit step")
    cause, _ = DiagnosticEngine.diagnose(err_timeout)
    assert cause == FailureRootCause.GATEWAY_OR_BANK_DOWNTIME
