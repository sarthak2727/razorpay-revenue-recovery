from datetime import datetime
from typing import Dict, Any, Optional
from app.models.schemas import RecoveryIncident, RecoveryStatus, AuditLogEntry
from app.core.guardrails import SafetyGuardrails

class InvalidStateTransitionError(Exception):
    pass

class RecoveryStateMachine:
    """
    Finite State Machine governing the lifecycle of a revenue recovery incident.
    Ensures state transitions are deterministic, verifiable, and logged to the audit trail.
    """
    
    ALLOWED_TRANSITIONS = {
        RecoveryStatus.DETECTED: [RecoveryStatus.DIAGNOSED, RecoveryStatus.PERMANENTLY_ABANDONED],
        RecoveryStatus.DIAGNOSED: [RecoveryStatus.ACTION_QUEUED, RecoveryStatus.PERMANENTLY_ABANDONED, RecoveryStatus.RECOVERED],
        RecoveryStatus.ACTION_QUEUED: [RecoveryStatus.ENGAGED, RecoveryStatus.COOLING_OFF, RecoveryStatus.PERMANENTLY_ABANDONED, RecoveryStatus.RECOVERED],
        RecoveryStatus.ENGAGED: [RecoveryStatus.RECOVERED, RecoveryStatus.COOLING_OFF, RecoveryStatus.EXHAUSTED_MAX_RETRIES, RecoveryStatus.OPTED_OUT, RecoveryStatus.PERMANENTLY_ABANDONED],
        RecoveryStatus.COOLING_OFF: [RecoveryStatus.ENGAGED, RecoveryStatus.RECOVERED, RecoveryStatus.EXHAUSTED_MAX_RETRIES, RecoveryStatus.OPTED_OUT, RecoveryStatus.PERMANENTLY_ABANDONED],
        RecoveryStatus.RECOVERED: [],  # Terminal
        RecoveryStatus.EXHAUSTED_MAX_RETRIES: [],  # Terminal
        RecoveryStatus.OPTED_OUT: [],  # Terminal
        RecoveryStatus.PERMANENTLY_ABANDONED: [],  # Terminal
    }

    @classmethod
    def transition(
        cls,
        incident: RecoveryIncident,
        new_status: RecoveryStatus,
        action_name: str,
        reason: str,
        rule_or_model: str = "DeterministicRulesEngine",
        metadata: Optional[Dict[str, Any]] = None
    ) -> RecoveryIncident:
        old_status = incident.current_status
        
        # Check transition legality
        valid_next_states = cls.ALLOWED_TRANSITIONS.get(old_status, [])
        if new_status not in valid_next_states and old_status != new_status:
            raise InvalidStateTransitionError(
                f"Illegal state transition from {old_status.value} to {new_status.value} for incident {incident.incident_id}"
            )
        
        timestamp_str = datetime.utcnow().isoformat() + "Z"
        metadata = metadata or {}
        
        # Cryptographic audit hash
        audit_hash = SafetyGuardrails.generate_audit_hash(
            incident_id=incident.incident_id,
            action=action_name,
            state_from=old_status.value,
            state_to=new_status.value,
            timestamp=timestamp_str,
            payload_data=metadata
        )
        
        audit_entry = {
            "timestamp": timestamp_str,
            "incident_id": incident.incident_id,
            "state_from": old_status.value,
            "state_to": new_status.value,
            "action_taken": action_name,
            "rule_or_model": rule_or_model,
            "reason": reason,
            "metadata": metadata,
            "payload_hash": audit_hash
        }
        
        incident.current_status = new_status
        incident.audit_trail.append(audit_entry)
        
        return incident
