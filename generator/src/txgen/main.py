import time
import random
import click
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from txgen.config import config
from txgen.population import EntityPopulation
from txgen.behavior import NormalBehaviorGenerator
from txgen.fraud_rings import FraudRingGenerator
from txgen.typologies import TypologyGenerator
from txgen.labels import LabelManager

@click.group()
def cli():
    """AegisFlow Synthetic Transaction Generator & AML Typology Engine CLI"""
    pass

@cli.command("seed-entities")
@click.option("--num-accounts", default=1000, help="Number of accounts to generate")
@click.option("--num-devices", default=500, help="Number of devices to generate")
@click.option("--num-ips", default=400, help="Number of IPs to generate")
@click.option("--num-merchants", default=200, help="Number of merchants to generate")
def seed_entities(num_accounts, num_devices, num_ips, num_merchants):
    """Seed entity population into PostgreSQL."""
    pop = EntityPopulation(seed=config.random_seed)
    pop.seed_entities(num_accounts=num_accounts, num_devices=num_devices, num_ips=num_ips, num_merchants=num_merchants)
    pop.persist_to_db(config.db_url)

@cli.command("generate-batch")
@click.option("--count", default=5000, help="Total transactions to generate")
@click.option("--fraud-ratio", default=0.05, help="Proportion of fraudulent transactions")
def generate_batch(count, fraud_ratio):
    """Generate a batch of synthetic transactions with injected fraud patterns."""
    pop = EntityPopulation(seed=config.random_seed)
    pop.seed_entities(num_accounts=500, num_devices=250, num_ips=200, num_merchants=100)
    pop.persist_to_db(config.db_url)

    normal_gen = NormalBehaviorGenerator(pop.accounts, pop.devices, pop.ips, pop.merchants, seed=config.random_seed)
    ring_gen = FraudRingGenerator(pop.accounts, pop.devices, pop.ips, seed=config.random_seed)
    typology_gen = TypologyGenerator(pop.accounts, pop.devices, pop.ips, seed=config.random_seed)

    print(f"Generating {count} batch transactions (Fraud Ratio: {fraud_ratio * 100}%)...")
    normal_count = int(count * (1 - fraud_ratio))
    transactions = normal_gen.generate_batch(count=normal_count)

    # Inject Fraud Rings
    ring_result = ring_gen.inject_shared_device_ring(ring_size=6)
    transactions.extend(ring_result["transactions"])

    # Persist Ring Edges into PostgreSQL
    engine = create_engine(config.db_url)
    with engine.begin() as conn:
        for edge in ring_result["edges"]:
            conn.execute(
                text("""
                    INSERT INTO entity_edges (id, source_id, source_type, target_id, target_type, edge_type, weight)
                    VALUES (:id, :src, :src_t, :tgt, :tgt_t, :e_type, :w)
                    ON CONFLICT (id) DO NOTHING
                """),
                {"id": edge["id"], "src": edge["source_id"], "src_t": edge["source_type"], "tgt": edge["target_id"], "tgt_t": edge["target_type"], "e_type": edge["edge_type"], "w": edge["weight"]}
            )

    # Inject AML Typologies
    transactions.extend(typology_gen.inject_smurfing(fan_in_count=4))
    transactions.extend(typology_gen.inject_layering(hop_count=4))
    transactions.extend(typology_gen.inject_round_tripping(loop_length=3))

    # Sort all by timestamp
    transactions.sort(key=lambda x: x["timestamp"])

    label_mgr = LabelManager(config.db_url)
    label_mgr.persist_transactions_and_labels(transactions)
    print(f"Batch generation completed! Total transactions: {len(transactions)}")

@cli.command("inject-typology")
@click.option("--typology", type=click.Choice(["smurfing", "layering", "round_tripping"]), required=True)
def inject_typology(typology):
    """Inject a specific AML typology on-demand."""
    pop = EntityPopulation(seed=config.random_seed)
    pop.seed_entities(num_accounts=100, num_devices=50, num_ips=50, num_merchants=20)
    pop.persist_to_db(config.db_url)

    typology_gen = TypologyGenerator(pop.accounts, pop.devices, pop.ips, seed=config.random_seed)

    if typology == "smurfing":
        txs = typology_gen.inject_smurfing(fan_in_count=5)
    elif typology == "layering":
        txs = typology_gen.inject_layering(hop_count=4)
    else:
        txs = typology_gen.inject_round_tripping(loop_length=3)

    label_mgr = LabelManager(config.db_url)
    label_mgr.persist_transactions_and_labels(txs)
    print(f"Typology '{typology}' injected with {len(txs)} transactions.")

@cli.command("stream")
@click.option("--rate", default=5, help="Transactions per second")
def stream(rate):
    """Stream real-time transactions into database."""
    print(f"Streaming transactions at ~{rate} TPS. Press Ctrl+C to stop.")
    pop = EntityPopulation(seed=config.random_seed)
    pop.seed_entities(num_accounts=200, num_devices=100, num_ips=100, num_merchants=50)
    pop.persist_to_db(config.db_url)

    normal_gen = NormalBehaviorGenerator(pop.accounts, pop.devices, pop.ips, pop.merchants)
    label_mgr = LabelManager(config.db_url)

    delay = 1.0 / rate
    while True:
        tx = normal_gen.generate_transaction(base_timestamp=datetime.now(timezone.utc))
        label_mgr.persist_transactions_and_labels([tx])
        print(f"Streamed transaction {tx['id']} | Amount: ${tx['amount']} | Channel: {tx['channel']}")
        time.sleep(delay)

if __name__ == "__main__":
    cli()
