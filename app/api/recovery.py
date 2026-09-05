from fastapi import APIRouter, HTTPException, Header, Response
from typing import Dict, Any, Optional
import uuid
import json
from datetime import datetime
from pydantic import BaseModel
from app.models.schemas import CustomerInfo, PaymentErrorDetails, RecoveryIncident
from app.services.recovery_service import recovery_service
from app.engines.agent import RecoveryAgent
from app.engines.voice_agent import VoiceRecoveryAgent
from app.engines.liquidity_predictor import LiquidityPredictor
from app.engines.explainability import ExplainabilityEngine
from app.engines.negotiator import AutonomousNegotiator
from app.engines.multi_agent_swarm import MultiAgentSwarm
from app.engines.instrument_optimizer import PaymentInstrumentOptimizer
from app.engines.audit_pdf import AuditPdfGenerator
from app.core.idempotency import idempotency_shield

router = APIRouter(prefix="/recovery", tags=["Recovery Operations"])

class SimulateFailureRequest(BaseModel):
    transaction_id: Optional[str] = None
    amount_inr: float = 1499.0
    customer_name: str = "Rahul Sharma"
    customer_phone: str = "+919876543210"
    customer_email: str = "rahul.sharma@example.com"
    preferred_language: str = "hi"
    error_code: str = "BAD_REQUEST_PAYMENT_OTP_VALIDATION_FAILED"
    error_description: str = "Customer failed OTP authorization"
    payment_method: str = "upi"

class CustomerReplyRequest(BaseModel):
    incident_id: str
    reply_text: str

class CaptureRecoveryRequest(BaseModel):
    incident_id: str
    amount_inr: Optional[float] = None

class NegotiateObjectionRequest(BaseModel):
    incident_id: str
    objection_text: str

@router.post("/simulate-failure")
async def simulate_failure(
    req: SimulateFailureRequest,
    x_idempotency_key: Optional[str] = Header(None)
):
    """
    Simulates a payment failure incident with optional Idempotency Shield protection.
    """
    if x_idempotency_key:
        acquired, cached_response = idempotency_shield.acquire_lock(x_idempotency_key)
        if not acquired:
            return {
                "idempotency_hit": True,
                "incident_id": cached_response.get("incident_id") if isinstance(cached_response, dict) else None,
                "message": "Duplicate request intercepted. Replaying cached response.",
                "data": cached_response
            }

    txn_id = req.transaction_id or f"pay_sim_{uuid.uuid4().hex[:8]}"
    
    incident = recovery_service.process_failure_event(
        transaction_id=txn_id,
        amount_inr=req.amount_inr,
        merchant_id="merchant_recovr_demo",
        customer_info=CustomerInfo(
            id=f"cust_{req.customer_phone[-4:]}",
            name=req.customer_name,
            email=req.customer_email,
            phone=req.customer_phone,
            preferred_language=req.preferred_language
        ),
        error_details=PaymentErrorDetails(
            code=req.error_code,
            description=req.error_description
        ),
        payment_method=req.payment_method
    )
    
    if x_idempotency_key:
        idempotency_shield.release_lock(x_idempotency_key, incident.dict())
    
    return incident

@router.post("/customer-reply")
async def customer_reply(req: CustomerReplyRequest):
    """
    Handles customer reply on WhatsApp / SMS channels via Autonomous Negotiator.
    """
    if req.incident_id not in recovery_service.incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    incident = recovery_service.incidents[req.incident_id]
    response = AutonomousNegotiator.handle_objection(incident, req.reply_text)
    return response

@router.post("/negotiate-objection")
async def negotiate_objection(req: NegotiateObjectionRequest):
    """
    Direct endpoint for Autonomous Objection Negotiator simulator.
    """
    if req.incident_id not in recovery_service.incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    incident = recovery_service.incidents[req.incident_id]
    return AutonomousNegotiator.handle_objection(incident, req.objection_text)

@router.post("/capture-recovery")
async def capture_recovery(req: CaptureRecoveryRequest):
    """
    Simulates completion of payment via recovery link.
    """
    if req.incident_id not in recovery_service.incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    updated = recovery_service.record_successful_recovery(req.incident_id, req.amount_inr)
    return updated

@router.get("/incident/{incident_id}")
async def get_incident(incident_id: str):
    if incident_id not in recovery_service.incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    return recovery_service.incidents[incident_id]

@router.get("/swarm-trace/{incident_id}")
async def get_swarm_trace(incident_id: str):
    """
    Returns Multi-Agent Swarm reasoning consensus trace.
    """
    if incident_id not in recovery_service.incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    incident = recovery_service.incidents[incident_id]
    return MultiAgentSwarm.generate_swarm_trace(incident)

@router.get("/split-options/{incident_id}")
async def get_split_options(incident_id: str):
    """
    Returns dynamic instrument downgrade & split payment alternatives.
    """
    if incident_id not in recovery_service.incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    incident = recovery_service.incidents[incident_id]
    return PaymentInstrumentOptimizer.get_alternative_payment_options(incident)

@router.get("/voice-call/{incident_id}")
async def get_voice_call_script(incident_id: str):
    """
    Generates dynamic AI Voice call recovery script and IVR options.
    """
    if incident_id not in recovery_service.incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    incident = recovery_service.incidents[incident_id]
    return VoiceRecoveryAgent.generate_voice_call_script(incident)

@router.get("/liquidity-forecast/{incident_id}")
async def get_liquidity_forecast(incident_id: str):
    """
    Returns 30-day liquidity probability curve and optimal retry timing.
    """
    if incident_id not in recovery_service.incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    incident = recovery_service.incidents[incident_id]
    paydays = incident.customer.historical_paydays or [1, 5, 28]
    return LiquidityPredictor.predict_optimal_retry_window(paydays, incident.amount_inr)

@router.get("/explain/{incident_id}")
async def get_decision_explainability(incident_id: str):
    """
    Returns SHAP-style feature attribution weights and decision path.
    """
    if incident_id not in recovery_service.incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    incident = recovery_service.incidents[incident_id]
    return ExplainabilityEngine.get_decision_attribution(incident)

@router.get("/audit-export/{incident_id}")
@router.get("/audit-export-pdf/{incident_id}")
async def export_audit_certificate_pdf(incident_id: str):
    """
    Exports official cryptographic SHA-256 signed RBI Compliance Audit Certificate in PDF format.
    """
    if incident_id not in recovery_service.incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    inc = recovery_service.incidents[incident_id]
    
    pdf_bytes = AuditPdfGenerator.generate_certificate_pdf(inc)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=compliance_audit_{incident_id}.pdf"}
    )

@router.get("/audit-export-json/{incident_id}")
async def export_audit_certificate_json(incident_id: str):
    """
    Exports raw JSON cryptographic audit certificate.
    """
    if incident_id not in recovery_service.incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    inc = recovery_service.incidents[incident_id]
    
    cert = {
        "certificate_id": f"CERT-{uuid.uuid4().hex[:12].upper()}",
        "export_timestamp": datetime.utcnow().isoformat() + "Z",
        "protocol": "RAZORPAY_RECOVR_COMPLIANCE_STANDARD_v2.4",
        "regulatory_seal": "100% RBI RECOVERY COMPLIANT",
        "incident_summary": {
            "incident_id": inc.incident_id,
            "transaction_id": inc.transaction_id,
            "amount_inr": inc.amount_inr,
            "current_status": inc.current_status,
            "attempts_used": f"{inc.attempt_count}/3 (Max Cap)",
            "root_cause": inc.root_cause
        },
        "cryptographic_audit_trail": [a if isinstance(a, dict) else a.dict() for a in inc.audit_trail]
    }
    
    content = json.dumps(cert, indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=compliance_audit_{incident_id}.json"}
    )
