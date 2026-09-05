import hashlib
import json
from datetime import datetime, timedelta
from typing import Tuple, Dict, Any, Optional
from app.models.schemas import RecoveryIncident, RecoveryStatus, FailureRootCause, RecoveryStrategy
from app.core.config import settings

class ComplianceViolationError(Exception):
    pass

class SafetyGuardrails:
    """
    FINTECH SAFETY & COMPLIANCE INVARIANTS:
    Enforces deterministic safety, RBI dunning guidelines, and anti-harassment rules.
    """
    
    @staticmethod
    def check_engagement_eligibility(incident: RecoveryIncident) -> Tuple[bool, str]:
        """
        Determines if the system is legally & safely allowed to interact with the customer.
        """
        # 1. Opt-out check
        if incident.is_opted_out:
            return False, "Customer previously opted out (Do Not Disturb / STOP registered)."
        
        # 2. Maximum attempts hard cap
        if incident.attempt_count >= settings.MAX_RECOVERY_ATTEMPTS:
            return False, f"Maximum retry ceiling ({settings.MAX_RECOVERY_ATTEMPTS}) reached. Halting dunning."
        
        # 3. Fraud / Risk flag check
        if incident.root_cause == FailureRootCause.FRAUD_RISK_FLAGGED:
            return False, "Incident flagged as suspicious/fraudulent by Risk Shield. Auto-dunning prohibited."
        
        # 4. Status check
        if incident.current_status in [RecoveryStatus.RECOVERED, RecoveryStatus.OPTED_OUT, RecoveryStatus.PERMANENTLY_ABANDONED]:
            return False, f"Incident is already terminal ({incident.current_status.value})."
        
        # 5. Cooling period check
        if incident.last_action_timestamp:
            elapsed_hours = (datetime.utcnow() - incident.last_action_timestamp).total_seconds() / 3600.0
            if elapsed_hours < settings.MIN_COOLING_PERIOD_HOURS:
                remaining = round(settings.MIN_COOLING_PERIOD_HOURS - elapsed_hours, 1)
                return False, f"In cooling-off window to prevent customer fatigue. {remaining}h remaining."
        
        return True, "Passed all safety & compliance checks."

    @staticmethod
    def check_rbi_time_compliance(current_hour_ist: int = 14) -> Tuple[bool, str]:
        """
        RBI Fair Practices Code prohibits collection/recovery communications outside 08:00 to 19:00 IST.
        """
        if not (8 <= current_hour_ist <= 19):
            return False, f"Outside permissible communication hours ({current_hour_ist}:00 IST). Queueing for 09:00 IST."
        return True, "Within permissible regulatory communication hours."

    @staticmethod
    def detect_opt_out_intent(message_text: str) -> bool:
        """
        Detects if customer reply indicates opt-out or stop command.
        """
        normalized = message_text.strip().upper()
        for kw in settings.AUTO_OPT_OUT_KEYWORDS:
            if kw in normalized:
                return True
        return False

    @staticmethod
    def generate_audit_hash(incident_id: str, action: str, state_from: str, state_to: str, timestamp: str, payload_data: Dict[str, Any]) -> str:
        """
        Generates a SHA-256 cryptographic proof to guarantee audit trail immutability.
        """
        serialized = json.dumps({
            "incident_id": incident_id,
            "action": action,
            "state_from": state_from,
            "state_to": state_to,
            "timestamp": timestamp,
            "payload": payload_data
        }, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
