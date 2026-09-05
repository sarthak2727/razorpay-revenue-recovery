import os
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "Razorpay Recovr AI — Sentinel Revenue Recovery"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Razorpay Credentials (defaults to test mode keys if not set)
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "rzp_test_buildathon_demo")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "secret_buildathon_test_key")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "webhook_secret_buildathon_2026")
    
    # Compliance & Safety Invariants
    MAX_RECOVERY_ATTEMPTS: int = 3
    MIN_COOLING_PERIOD_HOURS: int = 18  # Minimum wait time between customer outreach
    AUTO_OPT_OUT_KEYWORDS: list = ["STOP", "UNSUBSCRIBE", "DONOTCALL", "NO", "ROKO", "BAND KARO"]
    
    # Simulation & rails
    SIMULATION_MODE: bool = True
    ESTIMATED_COST_PER_RECOVERY_INR: float = 12.50 # SMS + WhatsApp API + Compute amortized cost

settings = Settings()
