import os
import json
from dotenv import load_dotenv
import asyncio

# Load .env
load_dotenv()

from services.ghl import fetch_inventory_async

async def test_ipanema():
    inventory = await fetch_inventory_async()
    ipanemas = [v for v in inventory if "ipanema" in v.get("titulo", "").lower()]
    if not ipanemas:
        print("❌ Nenhuma Ipanema encontrada!")
        return
    
    print(f"✅ Encontradas {len(ipanemas)} Ipanemas.")
    for v in ipanemas:
        print(f"--- {v.get('titulo')} ---")
        print(f"Ano: {v.get('ano')}")
        print(f"KM: {v.get('quilometragem')}")
        print(f"Preço: {v.get('preco')}")
        print(f"Câmbio: {v.get('cambio')}")
        print(f"Keys: {v.keys()}")

if __name__ == "__main__":
    asyncio.run(test_ipanema())
