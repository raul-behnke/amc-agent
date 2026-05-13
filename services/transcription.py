"""
Serviço de Transcrição — OpenAI Whisper.
Responsável por transformar áudios de leads em texto para o Lucas processar.
"""

import os

import httpx
from curl_cffi.requests import Session
from loguru import logger


_MIME_MAP = {
    ".ogg": "audio/ogg",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
    ".webm": "audio/webm",
}

_OGG_MAGIC = b"OggS"


def _detect_mime(url: str) -> tuple[str, str]:
    """Retorna (filename, mime_type) baseado na extensão da URL."""
    ext = "." + url.split("/")[-1].split("?")[0].rsplit(".", 1)[-1].lower()
    mime = _MIME_MAP.get(ext, "audio/mp4")
    filename = f"audio{ext}"
    return filename, mime


def _download_audio(audio_url: str) -> bytes | None:
    """Baixa áudio do GHL usando curl_cffi para bypass de Cloudflare."""
    try:
        with Session(impersonate="chrome", timeout=30) as s:
            resp = s.get(audio_url)
            resp.raise_for_status()
            return resp.content
    except Exception as e:
        logger.error("Erro no download do áudio: {err}", err=str(e))
        return None


async def transcrever_audio_ghl(audio_url: str) -> str:
    """Baixa o áudio do GHL e transcreve usando a API da OpenAI."""
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        logger.error("OPENAI_API_KEY não configurada para transcrição.")
        return _fallback_msg()

    filename, mime = _detect_mime(audio_url)
    logger.info("Iniciando transcrição | file={} | mime={}", filename, mime)

    # 1. Download via curl_cffi (bypass Cloudflare)
    audio_data = _download_audio(audio_url)
    if not audio_data:
        return _fallback_msg()

    content_size = len(audio_data)
    logger.info("Áudio baixado | size={} bytes", content_size)

    if content_size < 100:
        logger.warning("Arquivo suspeito — muito pequeno ({} bytes)", content_size)
        return _fallback_msg()

    # Corrigir MIME: GHL usa .mp4 mas o conteúdo real é OGG
    if audio_data[:4] == _OGG_MAGIC and mime != "audio/ogg":
        logger.info("Detectado OGG dentro de .mp4 — ajustando MIME")
        mime = "audio/ogg"
        filename = "audio.ogg"

    # 2. Transcrição via Whisper (httpx — sem Cloudflare)
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            files = {
                "file": (filename, audio_data, mime),
                "model": (None, "whisper-1"),
            }
            headers = {"Authorization": f"Bearer {openai_key}"}

            resp = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers=headers,
                files=files,
            )
            resp.raise_for_status()

            text = resp.json().get("text", "")
            logger.info("Transcrição concluída: {t}", t=text[:120])
            return text

    except httpx.HTTPStatusError as e:
        logger.error(
            "Whisper HTTP error | status={} | body={}",
            e.response.status_code,
            e.response.text[:200],
        )
    except Exception as e:
        logger.error("Erro na transcrição Whisper: {err}", err=str(e))

    return _fallback_msg()


def _fallback_msg() -> str:
    return "[Áudio recebido — transcrição indisponível]"
