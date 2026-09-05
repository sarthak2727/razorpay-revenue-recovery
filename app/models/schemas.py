from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime

class FailureRootCause(str, Enum):
    GATEWAY_OR_BANK_DOWNTIME = "GATEWAY_OR_BANK_DOWNTIME"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    EXPIRED_INSTRUMENT = "EXPIRED_INSTRUMENT"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    MANDATE_DEBIT_DECLINE = "MANDATE_DEBIT_DECLINE"
    CART_ABANDONMENT = "CART_ABANDONMENT"
    FRAUD_RISK_FLAGGED = "FRAUD_RISK_FLAGGED"
    UNKNOWN = "UNKNOWN"

class RecoveryStrategy(str, Enum):
    SILENT_SMART_RETRY = "SILENT_SMART_RETRY"                   # Background retry via optimal gateway/rail without customer friction
    SALARY_ALIGNED_MANDATE_RETRY = "SALARY_ALIGNED_MANDATE_RETRY" # Schedule mandate execution for predicted liquid salary window
    DYNAMIC_PAYMENT_LINK = "DYNAMIC_PAYMENT_LINK"               # Generate single-use Razorpay payment link with custom expiry
    CONVERSATIONAL_HINGLISH_DUNNING = "CONVERSATIONAL_HINGLISH_DUNNING" # Interactive WhatsApp/SMS agent (English & Hinglish)
    ESCALATE_TO_MERCHANT = "ESCALATE_TO_MERCHANT"               # Human/Merchant intervention required
    COMPLIANT_TERMINATION = "COMPLIANT_TERMINATION"             # Stop further attempts due to safety/RBI rules

class RecoveryStatus(str, Enum):
    DETECTED = "DETECTED"
    DIAGNOSED = "DIAGNOSED"
    ACTION_QUEUED = "ACTION_QUEUED"
    ENGAGED = "ENGAGED"
    RECOVERED = "RECOVERED"
    COOLING_OFF = "COOLING_OFF"
    EXHAUSTED_MAX_RETRIES = "EXHAUSTED_MAX_RETRIES"
    OPTED_OUT = "OPTED_OUT"
    PERMANENTLY_ABANDONED = "PERMANENTLY_ABANDONED"

class CustomerInfo(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    preferred_language: str = "en"  # "en" or "hi" / "hinglish"
    historical_paydays: List[int] = Field(default_factory=lambda: [1, 5, 7, 28, 30]) # Days of month when balance is highest

class PaymentErrorDetails(BaseModel):
    code: str
    description: str
    source: Optional[str] = "gateway"  # "bank", "network", "gateway", "customer"
    step: Optional[str] = "payment_authentication"
    reason: Optional[str] = None

class WebhookEventPayload(BaseModel):
    event: str
    account_id: str = "acc_test_merchant_01"
    created_at: int
    payload: Dict[str, Any]

class RecoveryIncident(BaseModel):
    incident_id: str
    transaction_id: str
    order_id: Optional[str] = None
    invoice_id: Optional[str] = None
    subscription_id: Optional[str] = None
    merchant_id: str
    amount_inr: float
    currency: str = "INR"
    customer: CustomerInfo
    error_details: PaymentErrorDetails
    payment_method: str = "upi"  # upi, card, netbanking, mandate, emi
    
    # State tracking
    current_status: RecoveryStatus = RecoveryStatus.DETECTED
    root_cause: Optional[FailureRootCause] = None
    root_cause_reasoning: Optional[str] = None
    recommended_strategy: Optional[RecoveryStrategy] = None
    
    # Execution & Safety
    attempt_count: int = 0
    max_attempts: int = 3
    last_action_timestamp: Optional[datetime] = None
    next_scheduled_retry: Optional[datetime] = None
    generated_payment_link: Optional[str] = None
    is_opted_out: bool = False
    
    # Metrics
    recovered_amount_inr: float = 0.0
    recovery_timestamp: Optional[datetime] = None
    
    # Audit trail
    audit_trail: List[Dict[str, Any]] = Field(default_factory=list)

class AuditLogEntry(BaseModel):
    timestamp: str
    incident_id: str
    state_from: str
    state_to: str
    action_taken: str
    rule_or_model: str
    reason: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    payload_hash: str

class BatchEvaluationSummary(BaseModel):
    total_records: int
    total_at_risk_gmv_inr: float
    total_recovered_gmv_inr: float
    recovery_rate_percentage: float
    recoverable_cases_count: int
    unrecoverable_cases_count: int
    compliance_violations: int = 0
    average_recovery_time_hours: float
    cost_of_recovery_inr: float
    net_roi_multiplier: float
    breakdown_by_root_cause: Dict[str, Dict[str, Any]]
    exception_log: List[Dict[str, Any]]
