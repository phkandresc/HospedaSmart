# -*- coding: utf-8 -*-
"""
Traductor de protocolo entre los comandos JSON de la API y las órdenes de texto del Arduino.

Contrato JSON (API):
  {"type": "command", "id": "cmd_...", "device": "room101.fan", "action": "set_power", "params": {"on": true}}
Orden serial (Arduino):
  "VENT_ON\n" -> respuesta "OK:VENT_ON\n"
"""
from typing import Any


def command_to_serial(device: str, action: str, params: dict[str, Any]) -> str | None:
    """Traduce un comando JSON a la orden de texto que espera el Arduino."""
    device_lower = device.lower()

    # Control de Ventilador
    if device_lower in ("room101.fan", "fan"):
        if action == "set_power":
            return "VENT_ON" if params.get("on") else "VENT_OFF"

    # Control de Luz
    if device_lower in ("room101.light", "light"):
        if action == "set_power":
            return "LUZ_ON" if params.get("on") else "LUZ_OFF"

    # Control de Cerrojo / Puerta
    if device_lower in ("room101.lock", "lock"):
        if action == "set_locked":
            return "PUERTA_CERRAR" if params.get("locked") else "PUERTA_ABRIR"
        if action == "unlock":
            return "PUERTA_ABRIR"
        if action == "lock":
            return "PUERTA_CERRAR"

    return None
