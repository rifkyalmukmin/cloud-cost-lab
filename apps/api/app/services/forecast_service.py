"""Cost forecasting service.

Provides 30-day cost forecasts using moving average and linear trend.
Forecasts include confidence ranges and are never presented as exact values.
"""

from datetime import date, timedelta
from typing import Optional

from app.services.cost_service import cost_service


class ForecastService:
    def forecast_cost(
        self,
        reference_date: Optional[date] = None,
        days_ahead: int = 30,
    ) -> dict:
        """Generate 30-day cost forecast with confidence range.

        Uses both moving average and linear trend to provide
        expected value with lower/upper bounds.
        """
        ref = reference_date or date(2026, 8, 26)

        # Get 60 days of historical data for forecast
        start = ref - timedelta(days=59)
        trend = cost_service.get_trend(start, ref)

        if not trend["daily_costs"]:
            return {
                "error": "Insufficient historical data for forecast",
                "forecast": [],
            }

        daily_costs = [d["net_cost"] for d in trend["daily_costs"]]

        if len(daily_costs) < 7:
            return {
                "error": "Insufficient historical data (need at least 7 days)",
                "forecast": [],
            }

        # Calculate moving average (last 14 days)
        ma_window = min(14, len(daily_costs))
        moving_avg = sum(daily_costs[-ma_window:]) / ma_window

        # Calculate linear trend (simple linear regression)
        n = len(daily_costs)
        x = list(range(n))
        y = daily_costs
        x_mean = sum(x) / n
        y_mean = sum(y) / n

        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator

        intercept = y_mean - slope * x_mean

        # Calculate standard deviation for confidence bounds
        residuals = [y[i] - (slope * x[i] + intercept) for i in range(n)]
        variance = sum(r ** 2 for r in residuals) / max(1, n - 1)
        std_dev = variance ** 0.5

        # Generate forecast
        forecast_data = []
        for day_offset in range(1, days_ahead + 1):
            forecast_date = ref + timedelta(days=day_offset)
            x_future = n + day_offset - 1

            # Linear trend projection
            trend_value = slope * x_future + intercept

            # Moving average projection (assume stable)
            ma_value = moving_avg

            # Weighted average (70% trend, 30% MA)
            expected = 0.7 * trend_value + 0.3 * ma_value

            # Confidence bounds (±1.5 std dev for ~87% confidence)
            confidence_margin = 1.5 * std_dev
            lower_bound = max(0, expected - confidence_margin)
            upper_bound = expected + confidence_margin

            forecast_data.append({
                "date": forecast_date.isoformat(),
                "expected": round(expected, 2),
                "lower_bound": round(lower_bound, 2),
                "upper_bound": round(upper_bound, 2),
                "confidence": "MEDIUM",
            })

        # Monthly summary
        monthly_expected = sum(d["expected"] for d in forecast_data)
        monthly_lower = sum(d["lower_bound"] for d in forecast_data)
        monthly_upper = sum(d["upper_bound"] for d in forecast_data)

        return {
            "period_start": ref.isoformat(),
            "period_end": (ref + timedelta(days=days_ahead)).isoformat(),
            "method": "hybrid (linear trend + moving average)",
            "historical_days": len(daily_costs),
            "forecast_days": days_ahead,
            "daily_forecast": forecast_data,
            "monthly_summary": {
                "expected": round(monthly_expected, 2),
                "lower_bound": round(monthly_lower, 2),
                "upper_bound": round(monthly_upper, 2),
                "range_description": f"${monthly_lower:.2f} - ${monthly_upper:.2f}",
            },
        }


forecast_service = ForecastService()
