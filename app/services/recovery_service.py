import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.models.schemas import (
    RecoveryIncident,
    RecoveryStatus,
    FailureRootCause,
    RecoveryStrategy,
    PaymentErrorDetails,
    CustomerInfo,
    BatchEvaluationSummary
)
from app.core.guardrails import SafetyGuardrails
from app.core.state_machine import RecoveryStateMachine
from app.engines.diagnostics import DiagnosticEngine
from app.engines.strategies import StrategyPlanner
from app.engines.agent import RecoveryAgent
from app.integrations.razorpay_client import razorpay_client

class RecoveryService:
    """
    Central orchestration service managing the end-to-end revenue recovery pipeline.
    """
    
    def __init__(self):
        self.incidents: Dict[str, RecoveryIncident] = {}

    def process_failure_event(
        self,
        transaction_id: str,
        amount_inr: float,
        merchant_id: str,
        customer_info: CustomerInfo,
        error_details: PaymentErrorDetails,
        payment_method: str = "upi",
        order_id: Optional[str] = None,
        subscription_id: Optional[str] = None
    ) -> RecoveryIncident:
        """
        Main entrypoint: ingests a failed payment, diagnoses root cause,
        evaluates safety invariants, and queues/executes the recovery strategy.
        """
        incident_id = f"inc_{uuid.uuid4().hex[:10]}"
        
        # 1. Initialize Incident
        incident = RecoveryIncident(
            incident_id=incident_id,
            transaction_id=transaction_id,
            order_id=order_id,
            subscription_id=subscription_id,
            merchant_id=merchant_id,
            amount_inr=amount_inr,
            customer=customer_info,
            error_details=error_details,
            payment_method=payment_method,
            current_status=RecoveryStatus.DETECTED
        )
        
        # 2. Run Diagnostics
        root_cause, reasoning = DiagnosticEngine.diagnose(error_details, payment_method)
        incident.root_cause = root_cause
        incident.root_cause_reasoning = reasoning
        
        # Transition: DETECTED -> DIAGNOSED
        RecoveryStateMachine.transition(
            incident=incident,
            new_status=RecoveryStatus.DIAGNOSED,
            action_name="DIAGNOSE_ROOT_CAUSE",
            reason=reasoning,
            rule_or_model="DiagnosticEngine",
            metadata={"error_code": error_details.code, "classified_cause": root_cause.value}
        )
        
        # 3. Strategy Planning
        strategy, strat_reason, scheduled_time = StrategyPlanner.determine_strategy(incident)
        incident.recommended_strategy = strategy
        incident.next_scheduled_retry = scheduled_time
        
        # 4. Check Safety & Stopping Guardrails
        if strategy == RecoveryStrategy.COMPLIANT_TERMINATION:
            RecoveryStateMachine.transition(
                incident=incident,
                new_status=RecoveryStatus.PERMANENTLY_ABANDONED,
                action_name="HALT_DUNNING_RISK_GUARD",
                reason=strat_reason,
                rule_or_model="SafetyGuardrails",
                metadata={"fraud_or_risk": True}
            )
            self.incidents[incident_id] = incident
            return incident
            
        eligible, eligibility_reason = SafetyGuardrails.check_engagement_eligibility(incident)
        if not eligible:
            RecoveryStateMachine.transition(
                incident=incident,
                new_status=RecoveryStatus.COOLING_OFF if "cooling" in eligibility_reason.lower() else RecoveryStatus.PERMANENTLY_ABANDONED,
                action_name="SAFETY_GUARD_HOLD",
                reason=eligibility_reason,
                rule_or_model="SafetyGuardrails"
            )
            self.incidents[incident_id] = incident
            return incident
            
        # Transition: DIAGNOSED -> ACTION_QUEUED
        RecoveryStateMachine.transition(
            incident=incident,
            new_status=RecoveryStatus.ACTION_QUEUED,
            action_name="QUEUE_RECOVERY_STRATEGY",
            reason=strat_reason,
            rule_or_model="StrategyPlanner",
            metadata={"strategy": strategy.value, "scheduled_time": str(scheduled_time)}
        )
        
        # 5. Execute Action
        self._execute_strategy_action(incident)
        
        self.incidents[incident_id] = incident
        return incident

    def _execute_strategy_action(self, incident: RecoveryIncident):
        """
        Executes the specific strategy selected for this incident.
        """
        strat = incident.recommended_strategy
        
        if strat == RecoveryStrategy.SILENT_SMART_RETRY:
            # Increment attempt and schedule background retry
            incident.attempt_count += 1
            incident.last_action_timestamp = datetime.utcnow()
            RecoveryStateMachine.transition(
                incident=incident,
                new_status=RecoveryStatus.ENGAGED,
                action_name="DISPATCH_SILENT_SMART_RETRY",
                reason="Routing retry via Razorpay Optimizer alternate rails.",
                rule_or_model="SmartRouterRail",
                metadata={"attempt": incident.attempt_count}
            )
            
        elif strat in [RecoveryStrategy.DYNAMIC_PAYMENT_LINK, RecoveryStrategy.CONVERSATIONAL_HINGLISH_DUNNING]:
            msg_payload = RecoveryAgent.generate_outreach_message(incident)
            incident.attempt_count += 1
            incident.last_action_timestamp = datetime.utcnow()
            RecoveryStateMachine.transition(
                incident=incident,
                new_status=RecoveryStatus.ENGAGED,
                action_name="DISPATCH_CUSTOMER_OUTREACH",
                reason=f"Sent localized outreach on {msg_payload['channel']}.",
                rule_or_model="RecoveryAgent",
                metadata=msg_payload
            )
            
        elif strat == RecoveryStrategy.SALARY_ALIGNED_MANDATE_RETRY:
            incident.attempt_count += 1
            incident.last_action_timestamp = datetime.utcnow()
            RecoveryStateMachine.transition(
                incident=incident,
                new_status=RecoveryStatus.ENGAGED,
                action_name="SCHEDULE_MANDATE_RETRY",
                reason=f"Scheduled mandate debit for {incident.next_scheduled_retry}.",
                rule_or_model="MandateRetryScheduler",
                metadata={"scheduled_date": str(incident.next_scheduled_retry)}
            )

    def record_successful_recovery(self, incident_id: str, recovered_amount: Optional[float] = None) -> RecoveryIncident:
        """
        Marks an incident as successfully recovered when payment is captured.
        """
        if incident_id not in self.incidents:
            raise KeyError(f"Incident {incident_id} not found.")
            
        incident = self.incidents[incident_id]
        if incident.current_status == RecoveryStatus.RECOVERED:
            return incident
            
        amt = recovered_amount if recovered_amount is not None else incident.amount_inr
        incident.recovered_amount_inr = amt
        incident.recovery_timestamp = datetime.utcnow()
        
        RecoveryStateMachine.transition(
            incident=incident,
            new_status=RecoveryStatus.RECOVERED,
            action_name="PAYMENT_CAPTURED",
            reason=f"Successfully captured recovered payment of ₹{amt:,.2f}.",
            rule_or_model="PaymentConfirmationWebhook",
            metadata={"recovered_amount_inr": amt}
        )
        return incident

    def get_summary_metrics(self) -> Dict[str, Any]:
        """
        Computes aggregate metrics across all active and past incidents.
        """
        total_incidents = len(self.incidents)
        if total_incidents == 0:
            return {
                "total_incidents": 0,
                "total_at_risk_gmv_inr": 0.0,
                "total_recovered_gmv_inr": 0.0,
                "recovery_rate_percentage": 0.0,
                "recovered_count": 0,
                "active_in_progress": 0,
                "terminal_unrecovered": 0
            }
            
        total_at_risk = sum(i.amount_inr for i in self.incidents.values())
        total_recovered = sum(i.recovered_amount_inr for i in self.incidents.values() if i.current_status == RecoveryStatus.RECOVERED)
        recovered_count = sum(1 for i in self.incidents.values() if i.current_status == RecoveryStatus.RECOVERED)
        active_count = sum(1 for i in self.incidents.values() if i.current_status in [RecoveryStatus.ACTION_QUEUED, RecoveryStatus.ENGAGED, RecoveryStatus.COOLING_OFF])
        unrecovered_count = sum(1 for i in self.incidents.values() if i.current_status in [RecoveryStatus.EXHAUSTED_MAX_RETRIES, RecoveryStatus.OPTED_OUT, RecoveryStatus.PERMANENTLY_ABANDONED])
        
        rate = (total_recovered / total_at_risk * 100.0) if total_at_risk > 0 else 0.0
        
        return {
            "total_incidents": total_incidents,
            "total_at_risk_gmv_inr": round(total_at_risk, 2),
            "total_recovered_gmv_inr": round(total_recovered, 2),
            "recovery_rate_percentage": round(rate, 2),
            "recovered_count": recovered_count,
            "active_in_progress": active_count,
            "terminal_unrecovered": unrecovered_count
        }

recovery_service = RecoveryService()
