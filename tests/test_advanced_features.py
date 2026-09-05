import pytest
from datetime import datetime
from app.core.idempotency import IdempotencyShield
from app.engines.liquidity_predictor import LiquidityPredictor
from app.engines.explainability import ExplainabilityEngine
from app.engines.voice_agent import VoiceRecoveryAgent
from app.engines.negotiator import AutonomousNegotiator
from app.engines.bank_telemetry import BankHealthRadar
from app.engines.multi_agent_swarm import MultiAgentSwarm
from app.engines.instrument_optimizer import PaymentInstrumentOptimizer
from app.models.schemas import RecoveryIncident, FailureRootCause, RecoveryStrategy, CustomerInfo, PaymentErrorDetails, RecoveryStatus

def test_idempotency_shield_duplicate_prevention():
    shield = IdempotencyShield(ttl_seconds=3600)
    key = "idem_test_key_123"
    
    acquired, cached = shield.acquire_lock(key)
    assert acquired is True
    assert cached is None
    
    acquired2, cached2 = shield.acquire_lock(key)
    assert acquired2 is False
    assert cached2["status"] == "CONFLICT"
    
    shield.release_lock(key, {"incident_id": "inc_abc", "status": "ENGAGED"})
    
    acquired3, cached3 = shield.acquire_lock(key)
    assert acquired3 is False
    assert cached3["incident_id"] == "inc_abc"

def test_liquidity_predictor_curve_generation():
    forecast = LiquidityPredictor.predict_optimal_retry_window(
        paydays=[1, 5, 28],
        amount_inr=2499.0
    )
    
    assert "optimal_retry_timestamp" in forecast
    assert forecast["peak_success_probability"] >= 80.0
    assert len(forecast["daily_probability_curve"]) == 30
    
    payday_entry = next((d for d in forecast["daily_probability_curve"] if d["is_payday"]), None)
    assert payday_entry is not None
    assert payday_entry["liquidity_probability"] >= 0.70

def test_explainability_feature_attribution():
    inc = RecoveryIncident(
        incident_id="inc_exp_01",
        transaction_id="txn_exp_01",
        merchant_id="merch_01",
        amount_inr=1999.0,
        customer=CustomerInfo(id="c1", name="Test User", phone="+919999999999"),
        error_details=PaymentErrorDetails(code="GATEWAY_ERROR", description="Timeout"),
        root_cause=FailureRootCause.GATEWAY_OR_BANK_DOWNTIME,
        recommended_strategy=RecoveryStrategy.SILENT_SMART_RETRY
    )
    
    attr = ExplainabilityEngine.get_decision_attribution(inc)
    assert attr["selected_strategy"] == "SILENT_SMART_RETRY"
    assert attr["model_confidence_score"] > 90.0
    assert len(attr["feature_attribution"]) >= 3
    total_weights = sum(f["weight"] for f in attr["feature_attribution"])
    assert pytest.approx(total_weights, 0.01) == 1.0

def test_voice_agent_for_all_root_causes():
    for rc in FailureRootCause:
        inc = RecoveryIncident(
            incident_id=f"inc_voice_{rc.value}",
            transaction_id=f"txn_{rc.value}",
            merchant_id="merch_01",
            amount_inr=1499.0,
            customer=CustomerInfo(id="c1", name="Rahul Sharma", phone="+919876543210", preferred_language="hi"),
            error_details=PaymentErrorDetails(code="TEST_CODE", description="Test"),
            root_cause=rc
        )
        script_data = VoiceRecoveryAgent.generate_voice_call_script(inc)
        assert "spoken_script_devanagari" in script_data
        assert "spoken_script_hinglish" in script_data
        assert len(script_data["spoken_script_devanagari"]) > 10
        assert len(script_data["spoken_script_hinglish"]) > 10

def test_autonomous_negotiator_objections():
    inc = RecoveryIncident(
        incident_id="inc_neg_01",
        transaction_id="txn_neg_01",
        merchant_id="merch_01",
        amount_inr=2499.0,
        customer=CustomerInfo(id="c1", name="Priya Patel", phone="+919812345678"),
        error_details=PaymentErrorDetails(code="OTP_TIMEOUT", description="Timeout"),
        root_cause=FailureRootCause.AUTHENTICATION_FAILED,
        current_status=RecoveryStatus.ENGAGED
    )
    
    # 1. Discount request
    res_disc = AutonomousNegotiator.handle_objection(inc, "koi discount milega kya?")
    assert res_disc["action"] == "DISCOUNT_OFFERED"
    assert res_disc["adjusted_amount_inr"] < 2499.0
    
    # 2. Liquidity crunch / Grace period
    res_grace = AutonomousNegotiator.handle_objection(inc, "abhi paise nahi hai salary late hai")
    assert res_grace["action"] == "GRACE_PERIOD_GRANTED"
    assert res_grace["grace_period_days"] == 3
    assert inc.current_status == RecoveryStatus.COOLING_OFF
    
    # 3. Opt-out
    res_opt = AutonomousNegotiator.handle_objection(inc, "STOP")
    assert res_opt["action"] == "OPTED_OUT"
    assert inc.current_status == RecoveryStatus.OPTED_OUT

def test_bank_health_radar_telemetry():
    telemetry = BankHealthRadar.get_live_bank_telemetry()
    assert "nodes" in telemetry
    assert len(telemetry["nodes"]) >= 6
    assert telemetry["total_monitored_nodes"] >= 6
    assert any(b["code"] == "HDFC" for b in telemetry["nodes"])
    assert any(b["code"] == "AXIS" for b in telemetry["nodes"])

def test_multi_agent_swarm_trace():
    inc = RecoveryIncident(
        incident_id="inc_swarm_01",
        transaction_id="txn_swarm_01",
        merchant_id="merch_01",
        amount_inr=1499.0,
        customer=CustomerInfo(id="c1", name="Rahul Sharma", phone="+919876543210"),
        error_details=PaymentErrorDetails(code="GATEWAY_ERROR", description="Timeout"),
        root_cause=FailureRootCause.GATEWAY_OR_BANK_DOWNTIME
    )
    
    trace = MultiAgentSwarm.generate_swarm_trace(inc)
    assert trace["swarm_consensus"] == "CONSENSUS_REACHED"
    assert trace["agents_involved"] == 4
    assert len(trace["trace_steps"]) == 4

def test_payment_instrument_optimizer():
    inc = RecoveryIncident(
        incident_id="inc_opt_01",
        transaction_id="txn_opt_01",
        merchant_id="merch_01",
        amount_inr=3000.0,
        customer=CustomerInfo(id="c1", name="Rahul Sharma", phone="+919876543210"),
        error_details=PaymentErrorDetails(code="LIMIT_EXCEEDED", description="Limit"),
        root_cause=FailureRootCause.INSUFFICIENT_FUNDS
    )
    
    options = PaymentInstrumentOptimizer.get_alternative_payment_options(inc)
    assert len(options["alternative_options"]) == 3
    assert options["original_amount_inr"] == 3000.0
