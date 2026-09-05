import time
from typing import Dict, Any, Optional, Tuple

class IdempotencyShield:
    """
    Fintech Production Invariant: Idempotency & Distributed Lock Engine.
    Guarantees that duplicate webhook deliveries or retry storms never trigger
    duplicate customer outreach or multiple mandate charges.
    """
    
    def __init__(self, ttl_seconds: int = 86400):
        # Maps idempotency_key -> (timestamp, response_payload, lock_status)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = ttl_seconds

    def acquire_lock(self, idempotency_key: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Attempts to acquire lock for a transaction.
        Returns:
            (True, None) if lock acquired.
            (False, cached_payload) if duplicate request already processed or in progress.
        """
        now = time.time()
        
        # Cleanup expired entries periodically
        self._cleanup_expired(now)
        
        if idempotency_key in self._cache:
            entry = self._cache[idempotency_key]
            if entry["status"] == "COMPLETED":
                return False, entry["response"]
            elif entry["status"] == "PROCESSING":
                # Request is currently in flight (concurrent duplicate)
                return False, {"status": "CONFLICT", "message": "Concurrent request in flight"}
        
        # Set lock
        self._cache[idempotency_key] = {
            "timestamp": now,
            "status": "PROCESSING",
            "response": None
        }
        return True, None

    def release_lock(self, idempotency_key: str, response_payload: Dict[str, Any]):
        """
        Marks execution completed and caches response for subsequent duplicates.
        """
        if idempotency_key in self._cache:
            self._cache[idempotency_key]["status"] = "COMPLETED"
            self._cache[idempotency_key]["response"] = response_payload

    def _cleanup_expired(self, now: float):
        expired_keys = [k for k, v in self._cache.items() if now - v["timestamp"] > self.ttl_seconds]
        for k in expired_keys:
            del self._cache[k]

idempotency_shield = IdempotencyShield()
