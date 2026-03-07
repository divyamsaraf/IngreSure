"""
Seed script for Supabase. Menu/restaurant tables have been removed; this script is a no-op.
Use seed_user.py to create the demo user. Use seed_ingredient_knowledge.py for the knowledge base.
"""
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_data():
    logger.info("seed_data: Menu/restaurant schema removed. No tables to seed. Use seed_user.py or seed_ingredient_knowledge.py.")


if __name__ == "__main__":
    seed_data()
