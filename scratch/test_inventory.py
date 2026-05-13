import os
from dotenv import load_dotenv
import asyncio

# Load .env
load_dotenv()

from services.ghl import fetch_inventory_async

async def test_inventory():
    print(f"LOCATION: {os.getenv('GHL_LOCATION_ID')}")
    print(f"CUSTOM_VALUE_ID: {os.getenv('GHL_INVENTORY_CUSTOM_VALUE_ID')}")
    try:
        inventory = await fetch_inventory_async()
        print(f"✅ SUCESSO! Itens no estoque: {len(inventory)}")
    except Exception as e:
        print(f"❌ FALHA: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_inventory())
