# -*- coding: utf-8 -*-
"""
Adaptador de comunicación con el Gateway (WebSocket).

Mantiene el registro del socket activo para la habitación y gestiona
el envío de comandos y la espera del acuse de recibo (ack) con timeout.
"""
import asyncio
import json
import uuid
from typing import Any
from fastapi import WebSocket

# Almacena el socket activo del gateway (en esta fase para room101 / local)
_active_gateway_ws: WebSocket | None = None
# Futuros pendientes esperando respuesta: {cmd_id: asyncio.Future}
_pending_acks: dict[str, asyncio.Future[dict[str, Any]]] = {}


def register_gateway_connection(websocket: WebSocket) -> None:
    """Registra una nueva conexión activa del gateway."""
    global _active_gateway_ws
    _active_gateway_ws = websocket
    print("[GATEWAY-CLIENT] Gateway conectado exitosamente por WebSocket.", flush=True)


def unregister_gateway_connection(websocket: WebSocket) -> None:
    """Elimina la conexión activa del gateway si coincide."""
    global _active_gateway_ws
    if _active_gateway_ws == websocket:
        _active_gateway_ws = None
        print("[GATEWAY-CLIENT] Gateway desconectado.", flush=True)


def handle_incoming_message(message_data: dict[str, Any]) -> None:
    """Procesa mensajes que llegan del gateway (acks o eventos)."""
    msg_type = message_data.get("type")
    
    if msg_type == "ack":
        cmd_id = message_data.get("id")
        if cmd_id and cmd_id in _pending_acks:
            future = _pending_acks.pop(cmd_id)
            if not future.done():
                future.set_result(message_data)
    elif msg_type == "event":
        device = message_data.get("device")
        event_name = message_data.get("event")
        value = message_data.get("value")
        print(f"[GATEWAY-EVENT] Evento recibido: {device} -> {event_name} (valor: {value})", flush=True)


async def enviar_comando_dispositivo(
    device: str,
    action: str,
    params: dict[str, Any],
    timeout_s: float = 2.5
) -> bool:
    """
    Envía un comando JSON al gateway y espera confirmación (ack).
    Retorna True si el gateway/Arduino confirmó con éxito, False en timeout o error.
    """
    global _active_gateway_ws
    if _active_gateway_ws is None:
        print(f"[GATEWAY-CLIENT] Error: No hay ningún gateway conectado para {device}", flush=True)
        return False

    cmd_id = f"cmd_{uuid.uuid4().hex[:8]}"
    comando = {
        "type": "command",
        "id": cmd_id,
        "device": device,
        "action": action,
        "params": params,
        "timeout_ms": int(timeout_s * 1000)
    }

    loop = asyncio.get_running_loop()
    future = loop.create_future()
    _pending_acks[cmd_id] = future

    try:
        await _active_gateway_ws.send_text(json.dumps(comando))
        print(f"[GATEWAY-CLIENT] Enviado: {cmd_id} -> {device}.{action}({params})", flush=True)
        
        # Esperar acuse de recibo con límite de tiempo
        respuesta = await asyncio.wait_for(future, timeout=timeout_s)
        es_ok = bool(respuesta.get("ok", False))
        print(f"[GATEWAY-CLIENT] Ack recibido: {cmd_id} ok={es_ok}", flush=True)
        return es_ok
    except asyncio.TimeoutError:
        print(f"[GATEWAY-CLIENT] Timeout ({timeout_s}s) esperando ack para {cmd_id}", flush=True)
        return False
    except Exception as e:
        print(f"[GATEWAY-CLIENT] Error al enviar comando: {e}", flush=True)
        return False
    finally:
        _pending_acks.pop(cmd_id, None)
