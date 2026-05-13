"""
Teste de transcrição com URLs reais do GHL — usando curl_cffi.
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.transcription import transcrever_audio_ghl, _download_audio, _detect_mime

AUDIO_URLS = [
    "https://api.zoitech.com.br/conversations-assets/location/L2b97kq1i5tk1Fr51AsI/conversations/g4dzix2B0XNQ43A3t1cd/79a16eed-b5c5-4d54-b37a-625df97d0d88.mp4",
    "https://api.zoitech.com.br/conversations-assets/location/L2b97kq1i5tk1Fr51AsI/conversations/g4dzix2B0XNQ43A3t1cd/0a6eb1d0-a827-479e-b7de-e877d8dc82ba.mp4",
    "https://api.zoitech.com.br/conversations-assets/location/L2b97kq1i5tk1Fr51AsI/conversations/g4dzix2B0XNQ43A3t1cd/8876e74f-9bec-44f7-8801-3e4bb156e86f.mp4",
    "https://api.zoitech.com.br/conversations-assets/location/L2b97kq1i5tk1Fr51AsI/conversations/g4dzix2B0XNQ43A3t1cd/7c62150b-4dc1-44f0-ba3d-bbcbac5bdf5d.mp4",
    "https://api.zoitech.com.br/conversations-assets/location/L2b97kq1i5tk1Fr51AsI/conversations/g4dzix2B0XNQ43A3t1cd/0a76abd4-1a96-444d-93a0-e15b85a0706c.mp4",
    "https://api.zoitech.com.br/conversations-assets/location/L2b97kq1i5tk1Fr51AsI/conversations/g4dzix2B0XNQ43A3t1cd/acaf23f9-ea74-4403-ae55-39e06faca8d8.mp4",
]


async def main() -> None:
    print("=" * 60)
    print("TESTE DE TRANSCRIÇÃO — curl_cffi + Whisper")
    print("=" * 60)

    openai_key = os.getenv("OPENAI_API_KEY")
    ghl_token = os.getenv("GHL_PIT_TOKEN")
    print(f"\nOPENAI_API_KEY: {'OK' if openai_key else 'AUSENTE'}")
    print(f"GHL_PIT_TOKEN:  {'OK' if ghl_token else 'AUSENTE'}")

    # Etapa 1: Download de todos os áudios
    print("\n--- ETAPA 1: Download dos áudios ---")
    successful_downloads = []
    for i, url in enumerate(AUDIO_URLS):
        short_id = url.rsplit("/", 1)[-1][:12]
        filename, mime = _detect_mime(url)
        data = _download_audio(url)
        if data:
            magic = data[:4]
            print(f"  [{i+1}] {short_id}... | {len(data)} bytes | magic={magic} | {mime}")
            successful_downloads.append((i, url, data))
        else:
            print(f"  [{i+1}] {short_id}... | FALHOU")

    if not successful_downloads:
        print("\nNenhum download funcionou. Abortando.")
        return

    # Etapa 2: Transcrição completa dos que baixaram
    print(f"\n--- ETAPA 2: Transcrição ({len(successful_downloads)} áudios) ---")
    for idx, (i, url, data) in enumerate(successful_downloads):
        short_id = url.rsplit("/", 1)[-1][:12]
        print(f"\n  [{idx+1}] URL ...{short_id}")
        result = await transcrever_audio_ghl(url)
        is_error = result.startswith("[")
        if is_error:
            print(f"  ERRO: {result[:150]}")
        else:
            print(f"  TRANSCRIÇÃO: \"{result}\"")

    print("\n" + "=" * 60)
    print("TESTES CONCLUÍDOS")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
