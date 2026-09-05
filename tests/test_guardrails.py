import pytest
from datetime import datetime, timedelta
from app.models.schemas import (
    RecoveryIncident,
    RecoveryStatus,
    FailureRootCause,
    CustomerInfo,
    PaymentErrorDetails
)
from app.core.guardrails import SafetyGuardrails

def create_sample_incident(attempts=0, opted_out=False, root_cause=FailureRootCause.INSUFFICIENT_FUNDS, hours_ago=None):
    last_action = datetime.utcnow() - timedelta(hours=hours_ago) if hours_ago is not None else None
    return RecoveryIncident(
        incident_id="inc_test_001",
        transaction_id="txn_test_001",
        merchant_id="merch_test",
        amount_inr=1500.0,
        customer=CustomerInfo(id="c1", name="Test Customer", phone="+919999999999"),
        error_details=PaymentErrorDetails(code="BAD_REQUEST_PAYMENT_UPI_INSUFFICIENT_FUNDS", description="Low bal"),
        attempt_count=attempts,
        is_opted_out=opted_out,
        root_cause=root_cause,
        last_action_timestamp=last_action,
        current_status=RecoveryStatus.DETECTED
    )

def test_guardrails_opt_out_rejection():
    inc = create_sample_incident(opted_out=True)
    eligible, reason = SafetyGuardrails.check_engagement_eligibility(inc)
    assert eligible is False
    assert "opted out" in reason.lower()

def test_guardrails_max_attempts_exhausted():
    inc = create_sample_incident(attempts=3)
    eligible, reason = SafetyGuardrails.check_engagement_eligibility(inc)
    assert eligible is False
    assert "maximum retry ceiling" in reason.lower()

def test_guardrails_fraud_flag_halt():
    inc = create_sample_incident(root_cause=FailureRootCause.FRAUD_RISK_FLAGGED)
    eligible, reason = SafetyGuardrails.check_engagement_eligibility(inc)
    assert eligible is False
    assert "fraud" in reason.lower()

def test_guardrails_cooling_period():
    # Only 5 hours elapsed (minimum is 18h)
    inc = create_sample_incident(attempts=1, hours_ago=5)
    eligible, reason = SafetyGuardrails.check_engagement_eligibility(inc)
    assert eligible is False
    assert "cooling-off" in reason.lower()

def test_guardrails_cooling_period_passed():
    # 20 hours elapsed (cooling period satisfied)
    inc = create_sample_incident(attempts=1, hours_ago=20)
    eligible, reason = SafetyGuardrails.check_engagement_eligibility(inc)
    assert eligible is True

def test_opt_out_keyword_detection():
    assert SafetyGuardrails.detect_opt_out_intent("Please STOP messaging me") is True
    assert SafetyGuardrails.detect_opt_out_intent("BAND KARO") is True
    assert SafetyGuardrails.detect_opt_out_intent("unsubscribe") is True
    assert SafetyGuardrails.detect_opt_out_intent("I want to pay tomorrow") is False

def test_audit_hash_integrity():
    hash1 = SafetyGuardrails.generate_audit_hash("inc_1", "ACTION_A", "A", "B", "2026-08-27T00:00:00Z", {"amount": 100})
    hash2 = SafetyGuardrails.generate_audit_hash("inc_1", "ACTION_A", "A", "B", "2026-08-27T00:00:00Z", {"amount": 100})
    hash3 = SafetyGuardrails.generate_audit_hash("inc_1", "ACTION_A", "A", "B", "2026-08-27T00:00:00Z", {"amount": 200})
    
    assert hash1 == hash2
    assert hash1 != hash3
    assert len(hash1) == 64
