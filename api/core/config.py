# -*- coding: utf-8 -*-
import os

PORT: int = int(os.getenv("PORT", "8000"))
HOST: str = os.getenv("HOST", "0.0.0.0")

# Skill ID de Alexa (opcional en desarrollo, recomendado en producción)
SKILL_ID: str | None = os.getenv("SKILL_ID", None)

# Si es False, permite peticiones locales de prueba sin certificados SSL de Amazon.
# Para producción / ngrok con el Echo Dot real, debe ser True.
VERIFY_ALEXA_SIGNATURE: bool = os.getenv("VERIFY_ALEXA_SIGNATURE", "false").lower() in ("true", "1")
VERIFY_ALEXA_TIMESTAMP: bool = os.getenv("VERIFY_ALEXA_TIMESTAMP", "false").lower() in ("true", "1")
