"""Cost anomaly detection service.

Detects unexpected cost increases using rolling average and z-score.
"""

from datetime import date, timedelta
from typing import Optional

from app.clock import reference_today
from app.services.cost_service import cost_service
from app.services.mock_data import generate_cost_records


class AnomalyService:
    def detect_anomalies(
        self,
        reference_date: Optional[date] = None,
        lookback_days: int = 30,
    ) -> dict:
        """Detect cost anomalies using rolling average and z-score."""
        ref = reference_date or reference_today()
        start = ref - timedelta(days=lookback_days - 1)

        trend = cost_service.get_trend(start, ref)

        if not trend["daily_costs"] or len(trend["daily_costs"]) < 7:
            return {
                "error": "Insufficient data for anomaly detection (need at least 7 days)",
                "anomalies": [],
            }

        daily_costs = trend["daily_costs"]

        # Calculate rolling average and standard deviation
        window = min(14, len(daily_costs))
        anomalies = []

        for i in range(window, len(daily_costs)):
            window_data = [daily_costs[j]["net_cost"] for j in range(i - window, i)]
            current_cost = daily_costs[i]["net_cost"]

            avg = sum(window_data) / len(window_data)
            variance = sum((x - avg) ** 2 for x in window_data) / len(window_data)
            std_dev = variance ** 0.5

            if std_dev == 0:
                z_score = 0
            else:
                z_score = (current_cost - avg) / std_dev

            # Detect anomaly if z-score > 2.0 (95% confidence)
            if z_score > 2.0:
                difference = current_cost - avg
                percentage_change = (difference / avg * 100) if avg > 0 else 0

                severity = "HIGH" if z_score > 3.0 else "MEDIUM"

                # Get details by service/project/resource
                anomaly_date = date.fromisoformat(daily_costs[i]["date"])
                cost_records = generate_cost_records(anomaly_date, anomaly_date)

                # Find top contributors to the spike
                resource_costs = {}
                service_costs = {}
                project_costs = {}

                for record in cost_records:
                    rid = record["resource_id"]
                    service = record["service_name"]
                    project = record["project_name"]

                    resource_costs[rid] = resource_costs.get(rid, 0) + record["net_cost"]
                    service_costs[service] = service_costs.get(service, 0) + record["net_cost"]
                    project_costs[project] = project_costs.get(project, 0) + record["net_cost"]

                top_resource = max(resource_costs.items(), key=lambda x: x[1]) if resource_costs else ("", 0)
                top_service = max(service_costs.items(), key=lambda x: x[1]) if service_costs else ("", 0)
                top_project = max(project_costs.items(), key=lambda x: x[1]) if project_costs else ("", 0)

                anomalies.append({
                    "date": daily_costs[i]["date"],
                    "actual": round(current_cost, 2),
                    "expected": round(avg, 2),
                    "difference": round(difference, 2),
                    "percentage_change": round(percentage_change, 1),
                    "z_score": round(z_score, 2),
                    "severity": severity,
                    "confidence": "HIGH",
                    "top_service": top_service[0],
                    "top_service_cost": round(top_service[1], 2),
                    "top_project": top_project[0],
                    "top_project_cost": round(top_project[1], 2),
                    "top_resource": top_resource[0],
                    "top_resource_cost": round(top_resource[1], 2),
                })

        return {
            "period_start": start.isoformat(),
            "period_end": ref.isoformat(),
            "lookback_days": lookback_days,
            "method": "z-score (rolling average baseline)",
            "threshold": "z-score > 2.0",
            "anomalies": anomalies,
            "total_anomalies": len(anomalies),
        }


anomaly_service = AnomalyService()
