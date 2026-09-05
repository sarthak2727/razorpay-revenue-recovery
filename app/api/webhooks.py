from fastapi import APIRouter, Header, HTTPException, Request
from typing import Dict, Any, Optional
from app.models.schemas import CustomerInfo, PaymentErrorDetails
from app.services.recovery_service import recovery_service
from app.integrations.razorpay_client import razorpay_client

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

@router.post("/razorpay")
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None)
):
    """
    Endpoint listening for live Razorpay Webhooks:
    - payment.failed
    - subscription.halted
    - payment.captured (for recovery confirmation)
    """
    raw_body = await request.body()
    body_str = raw_body.decode("utf-8")
    
    if x_razorpay_signature:
        is_valid = razorpay_client.verify_webhook_signature(body_str, x_razorpay_signature)
        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid Razorpay Webhook Signature")
            
    payload = await request.json()
    event_type = payload.get("event")
    
    if not event_type:
        raise HTTPException(status_code=400, detail="Missing event type in payload")
        
    # Handle payment.failed
    if event_type == "payment.failed":
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        error_code = payment_entity.get("error_code", "UNKNOWN_ERROR")
        error_desc = payment_entity.get("error_description", "Payment failed")
        error_source = payment_entity.get("error_source", "gateway")
        error_reason = payment_entity.get("error_reason", None)
        
        amount_inr = float(payment_entity.get("amount", 0)) / 100.0
        contact = payment_entity.get("contact", "+919876543210")
        email = payment_entity.get("email", "customer@example.com")
        txn_id = payment_entity.get("id", "pay_mock_123")
        method = payment_entity.get("method", "upi")
        
        incident = recovery_service.process_failure_event(
            transaction_id=txn_id,
            amount_inr=amount_inr,
            merchant_id="merchant_razorpay_live",
            customer_info=CustomerInfo(
                id=f"cust_{contact[-6:]}",
                name="Merchant Customer",
                email=email,
                phone=contact,
                preferred_language="en"
            ),
            error_details=PaymentErrorDetails(
                code=error_code,
                description=error_desc,
                source=error_source,
                reason=error_reason
            ),
            payment_method=method,
            order_id=payment_entity.get("order_id")
        )
        return {"status": "success", "message": "Failure event processed", "incident": incident}
        
    # Handle payment.captured (Recovery verification)
    elif event_type == "payment.captured":
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        notes = payment_entity.get("notes", {})
        ref_incident_id = notes.get("incident_id")
        amount_inr = float(payment_entity.get("amount", 0)) / 100.0
        
        if ref_incident_id and ref_incident_id in recovery_service.incidents:
            updated = recovery_service.record_successful_recovery(ref_incident_id, amount_inr)
            return {"status": "success", "message": "Incident marked recovered", "incident": updated}
            
        return {"status": "ignored", "message": "Payment not associated with active recovery"}

    return {"status": "acknowledged", "event": event_type}
