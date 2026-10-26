import pytest
from datetime import datetime, timezone
from txgen.population import EntityPopulation
from txgen.behavior import NormalBehaviorGenerator
from txgen.fraud_rings import FraudRingGenerator
from txgen.typologies import TypologyGenerator

@pytest.fixture
def seeded_population():
    pop = EntityPopulation(seed=42)
    pop.seed_entities(num_accounts=50, num_devices=20, num_ips=20, num_merchants=10)
    return pop

def test_entity_population_generation(seeded_population):
    pop = seeded_population
    assert len(pop.accounts) == 50
    assert len(pop.devices) == 20
    assert len(pop.ips) == 20
    assert len(pop.merchants) == 10
    assert len(pop.edges) == 100 # 2 edges per account (device + ip)

def test_normal_behavior_generator(seeded_population):
    pop = seeded_population
    gen = NormalBehaviorGenerator(pop.accounts, pop.devices, pop.ips, pop.merchants, seed=42)
    tx = gen.generate_transaction(datetime.now(timezone.utc))
    
    assert tx["id"].startswith("tx_")
    assert tx["amount"] > 0.0
    assert tx["currency"] == "USD"
    assert tx["is_fraud"] is False
    assert tx["typology_type"] == "normal"

def test_fraud_ring_generator(seeded_population):
    pop = seeded_population
    ring_gen = FraudRingGenerator(pop.accounts, pop.devices, pop.ips, seed=42)
    result = ring_gen.inject_shared_device_ring(ring_size=5)
    
    assert len(result["transactions"]) == 5
    assert len(result["ring_accounts"]) == 5
    for tx in result["transactions"]:
        assert tx["is_fraud"] is True
        assert tx["typology_type"] == "fraud_ring"
        assert tx["device_id"] == result["shared_device_id"]

def test_smurfing_typology(seeded_population):
    pop = seeded_population
    typ_gen = TypologyGenerator(pop.accounts, pop.devices, pop.ips, seed=42)
    txs = typ_gen.inject_smurfing(fan_in_count=4)
    
    # 4 deposit transactions + 4 consolidation transactions = 8
    assert len(txs) == 8
    for tx in txs:
        assert tx["is_fraud"] is True
        assert tx["typology_type"] == "smurfing"
        assert 9000.0 <= tx["amount"] <= 10000.0

def test_layering_typology(seeded_population):
    pop = seeded_population
    typ_gen = TypologyGenerator(pop.accounts, pop.devices, pop.ips, seed=42)
    txs = typ_gen.inject_layering(hop_count=3)
    
    assert len(txs) == 3
    for tx in txs:
        assert tx["is_fraud"] is True
        assert tx["typology_type"] == "layering"
        assert tx["channel"] == "wire_transfer"

def test_round_tripping_typology(seeded_population):
    pop = seeded_population
    typ_gen = TypologyGenerator(pop.accounts, pop.devices, pop.ips, seed=42)
    txs = typ_gen.inject_round_tripping(loop_length=3)
    
    assert len(txs) == 3
    for tx in txs:
        assert tx["is_fraud"] is True
        assert tx["typology_type"] == "round_tripping"
    
    # Verify circular loop: source of first = target of last
    assert txs[0]["source_account_id"] == txs[-1]["target_account_id"]
