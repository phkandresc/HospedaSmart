# -*- coding: utf-8 -*-
"""
Proceso nativo del Gateway de HospedaSmart.

Conecta hacia la API mediante WebSocket saliente (ws://localhost:8000/ws/gateway)
y hacia el Arduino físico (o simulador de hardware) mediante serial_bridge.
"""
import os
import sys
import json
import asyncio
import datetime
import websockets

from gateway.serial_bridge import bridge, HardwareNoDisponible
from gateway.protocol import command_to_serial

API_WS_URL = os.getenv("API_WS_URL", "ws://localhost:8000/ws/gateway")


async def procesar_comando(ws, raw_msg: str):
    """Procesa un comando JSON recibido de la API, lo envía al Arduino y responde ack."""
    try:
        msg = json.loads(raw_msg)
    except json.JSONDecodeError:
        print(f"[GATEWAY] Mensaje recibido no es JSON válido: {raw_msg}", flush=True)
        return

    if msg.get("type") != "command":
        return

    cmd_id = msg.get("id")
    device = msg.get("device", "")
    action = msg.get("action", "")
    params = msg.get("params", {})

    print(f"\n[GATEWAY] 📥 Comando recibido: {cmd_id} | {device} -> {action}({params})", flush=True)

    orden_serial = command_to_serial(device, action, params)
    if orden_serial is None:
        print(f"[GATEWAY] ⚠️ Dispositivo o acción no reconocida por el protocolo: {device} / {action}", flush=True)
        ok = False
    else:
        # La lectura serie es bloqueante: se hace en un hilo para no congelar el WebSocket
        ok = await asyncio.to_thread(bridge.enviar, orden_serial)

    # Construir ack de confirmación
    ack = {
        "type": "ack",
        "id": cmd_id,
        "ok": ok,
        "device": device,
        "state": params,
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

    try:
        await ws.send(json.dumps(ack))
        print(f"[GATEWAY] 📤 Acuse enviado a la API: {cmd_id} (ok={ok})\n", flush=True)
    except Exception as e:
        print(f"[GATEWAY] Error al enviar ack: {e}", flush=True)


async def gateway_loop():
    bridge.conectar()

    while True:
        try:
            print(f"[GATEWAY] Conectando a la API en {API_WS_URL}...", flush=True)
            async with websockets.connect(API_WS_URL) as ws:
                print(f"[GATEWAY] ✅ Conexión WebSocket establecida con la API.", flush=True)
                async for message in ws:
                    await procesar_comando(ws, message)
        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError, OSError) as e:
            print(f"[GATEWAY] ⚠️ API no disponible ({e}). Reintentando en 3 segundos...", flush=True)
            await asyncio.sleep(3)
        except Exception as e:
            print(f"[GATEWAY] Error inesperado en bucle: {e}. Reintentando en 3 segundos...", flush=True)
            await asyncio.sleep(3)


def main():
    print("==================================================")
    print("      HospedaSmart - Gateway de Habitación       ")
    print("==================================================")
    try:
        asyncio.run(gateway_loop())
    except KeyboardInterrupt:
        print("\n[GATEWAY] Gateway detenido por el usuario.")
        sys.exit(0)
    except HardwareNoDisponible:
        sys.exit(1)


if __name__ == "__main__":
    main()
