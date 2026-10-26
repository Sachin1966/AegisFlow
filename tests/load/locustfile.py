import random
from locust import HttpUser, task, between

class FraudScoringUser(HttpUser):
    wait_time = between(0.001, 0.005) # Simulating high throughput / 300 TPS target profile

    @task(8)
    def score_normal_transaction(self):
        tx_id = f"tx_load_{random.randint(100000, 999999)}"
        payload = {
            "transaction": {
                "id": tx_id,
                "source_account_id": f"ACCT-{random.randint(1000, 5000)}",
                "target_account_id": f"ACCT-{random.randint(5001, 9999)}",
                "amount": round(random.uniform(15.0, 450.0), 2),
                "currency": "USD",
                "channel": "mobile_app",
                "device_id": f"DEV-{random.randint(100, 999)}"
            },
            "features": {
                "tx_count_1h": float(random.randint(0, 3)),
                "amt_sum_1h": float(random.uniform(50.0, 600.0)),
                "amt_deviation_zscore": float(random.gauss(0, 1)),
                "distance_to_known_fraud": float(random.choice([3.0, 4.0, 99.0])),
                "is_vpn_ip": 0.0
            },
            "degraded": False
        }
        with self.client.post("/api/v1/score", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("latency_ms", 0) > 100.0:
                    response.failure(f"Latency exceeded 100ms SLO: {data.get('latency_ms')}ms")
                else:
                    response.success()
            else:
                response.failure(f"Status code {response.status_code}")

    @task(2)
    def score_high_risk_transaction(self):
        tx_id = f"tx_load_risk_{random.randint(100000, 999999)}"
        payload = {
            "transaction": {
                "id": tx_id,
                "source_account_id": "ACCT-7842",
                "amount": round(random.uniform(9200.0, 9850.0), 2),
                "currency": "USD",
                "channel": "mobile_app",
                "device_id": "DEV-9812"
            },
            "features": {
                "tx_count_1h": 6.0,
                "amt_sum_1h": 58000.0,
                "amt_deviation_zscore": 3.9,
                "distance_to_known_fraud": 2.0,
                "is_vpn_ip": 1.0,
                "acct_count_per_device_24h": 6.0
            },
            "degraded": False
        }
        self.client.post("/api/v1/score", json=payload)
