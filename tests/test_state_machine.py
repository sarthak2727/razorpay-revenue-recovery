import pytest
from app.models.schemas import (
    RecoveryIncident,
    RecoveryStatus,
    CustomerInfo,
    PaymentErrorDetails
)
from app.core.state_machine import RecoveryStateMachine, InvalidStateTransitionError

def get_base_incident():
    return RecoveryIncident(
        incident_id="inc_sm_01",
        transaction_id="txn_sm_01",
        merchant_id="merch_01",
        amount_inr=1000.0,
        customer=CustomerInfo(id="c1", name="Alice", phone="+919876543210"),
        error_details=PaymentErrorDetails(code="GATEWAY_ERROR", description="Timeout"),
        current_status=RecoveryStatus.DETECTED
    )

def test_valid_state_transitions():
    inc = get_base_incident()
    assert inc.current_status == RecoveryStatus.DETECTED

    # DETECTED -> DIAGNOSED
    RecoveryStateMachine.transition(inc, RecoveryStatus.DIAGNOSED, "ACTION_DIAGNOSE", "Root cause identified")
    assert inc.current_status == RecoveryStatus.DIAGNOSED
    assert len(inc.audit_trail) == 1

    # DIAGNOSED -> ACTION_QUEUED
    RecoveryStateMachine.transition(inc, RecoveryStatus.ACTION_QUEUED, "ACTION_QUEUE", "Strategy ready")
    assert inc.current_status == RecoveryStatus.ACTION_QUEUED
    assert len(inc.audit_trail) == 2

    # ACTION_QUEUED -> ENGAGED
    RecoveryStateMachine.transition(inc, RecoveryStatus.ENGAGED, "ACTION_ENGAGE", "Outreach sent")
    assert inc.current_status == RecoveryStatus.ENGAGED

    # ENGAGED -> RECOVERED
    RecoveryStateMachine.transition(inc, RecoveryStatus.RECOVERED, "ACTION_CAPTURED", "Payment captured")
    assert inc.current_status == RecoveryStatus.RECOVERED

def test_illegal_state_transition_raises():
    inc = get_base_incident()
    # DETECTED cannot jump straight to ENGAGED without DIAGNOSED
    with pytest.raises(InvalidStateTransitionError):
        RecoveryStateMachine.transition(inc, RecoveryStatus.ENGAGED, "ACTION_ILLEGAL", "Bypassing diagnosis")
