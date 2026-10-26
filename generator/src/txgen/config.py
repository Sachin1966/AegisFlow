import os
from pydantic import BaseModel, Field

class GeneratorConfig(BaseModel):
    random_seed: int = Field(default=42, description="Seed for deterministic generation")
    num_accounts: int = Field(default=1000, description="Number of baseline accounts")
    num_devices: int = Field(default=500, description="Number of baseline devices")
    num_ips: int = Field(default=400, description="Number of baseline IP addresses")
    num_merchants: int = Field(default=200, description="Number of baseline merchants")
    default_currency: str = Field(default="USD")
    normal_tx_mean_amount: float = Field(default=120.50)
    normal_tx_std_amount: float = Field(default=85.00)
    fraud_ratio: float = Field(default=0.05, description="Proportion of fraudulent transactions")
    db_url: str = Field(
        default_factory=lambda: os.getenv("DATABASE_URL", "postgresql://aegis_user:aegis_password_secure@localhost:5432/aegisflow_db")
    )
    ingestion_url: str = Field(
        default_factory=lambda: os.getenv("INGESTION_SERVICE_URL", "http://localhost:8001")
    )

config = GeneratorConfig()
