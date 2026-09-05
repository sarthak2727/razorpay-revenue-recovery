import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional

class LiquidityPredictor:
    """
    Bayesian Liquidity & Salary-Cycle Predictor.
    Models the probability distribution of an Indian consumer or business account
    having sufficient liquidity over the next 30 days.
    """

    @classmethod
    def predict_optimal_retry_window(
        cls,
        paydays: List[int],
        amount_inr: float,
        current_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        now = current_date or datetime.utcnow()
        current_day = now.day
        
        paydays = sorted(paydays) if paydays else [1, 5, 28]
        
        # Calculate daily probability curve for 30 days
        daily_probabilities = []
        best_day_offset = 1
        max_prob = 0.0
        
        for offset in range(1, 31):
            future_date = now + timedelta(days=offset)
            f_day = future_date.day
            weekday = future_date.weekday() # 0 = Monday, 6 = Sunday
            
            # Base liquidity probability
            base_prob = 0.35
            
            # Proximity to payday boost
            min_dist_to_payday = min(abs(f_day - p) for p in paydays)
            if min_dist_to_payday == 0:
                base_prob = 0.94 # Direct payday
            elif min_dist_to_payday == 1:
                base_prob = 0.88 # 1 day after payday
            elif min_dist_to_payday == 2:
                base_prob = 0.79 # 2 days after payday
            elif min_dist_to_payday <= 4:
                base_prob = 0.65
                
            # Weekend penalty (banks process less smoothly, personal spending high)
            if weekday == 5: # Saturday
                base_prob *= 0.85
            elif weekday == 6: # Sunday
                base_prob *= 0.75
            elif weekday == 0: # Monday morning liquidity surge
                base_prob = min(base_prob * 1.15, 0.98)
                
            # Amount penalty for very large ticket sizes
            if amount_inr > 10000:
                base_prob *= 0.88
                
            prob_score = round(min(max(base_prob, 0.15), 0.98), 3)
            
            daily_probabilities.append({
                "day_offset": offset,
                "date": future_date.strftime("%Y-%m-%d"),
                "display_date": future_date.strftime("%d %b (%a)"),
                "liquidity_probability": prob_score,
                "is_payday": (f_day in paydays)
            })
            
            # Track best optimal day in the near window (1 to 7 days)
            if offset <= 7 and prob_score > max_prob:
                max_prob = prob_score
                best_day_offset = offset

        optimal_date = now + timedelta(days=best_day_offset)
        # Schedule at 10:15 AM (highest banking success window in India)
        optimal_timestamp = optimal_date.replace(hour=10, minute=15, second=0, microsecond=0)

        return {
            "optimal_retry_timestamp": optimal_timestamp.isoformat() + "Z",
            "optimal_display": optimal_timestamp.strftime("%d %b %Y, 10:15 AM IST"),
            "peak_success_probability": round(max_prob * 100, 1),
            "nearest_payday": next((p for p in paydays if p >= current_day), paydays[0]),
            "daily_probability_curve": daily_probabilities
        }
