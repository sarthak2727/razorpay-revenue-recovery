from fastapi import APIRouter
from typing import Dict, Any, List
from app.services.recovery_service import recovery_service
from app.engines.bank_telemetry import BankHealthRadar

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/metrics")
async def get_metrics():
    """
    Returns live recovery metrics, total GMV recovered, recovery rate, and status counts.
    """
    return recovery_service.get_summary_metrics()

@router.get("/incidents")
async def get_all_incidents(limit: int = 50):
    """
    Returns list of recent recovery incidents with audit trails and details.
    """
    incidents_list = list(recovery_service.incidents.values())
    return incidents_list[::-1][:limit]

@router.get("/bank-health")
async def get_bank_health_radar():
    """
    Returns real-time telemetry, latency, and success rates for top Indian issuer banks.
    """
    return BankHealthRadar.get_live_bank_telemetry()
