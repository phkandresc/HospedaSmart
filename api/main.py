# -*- coding: utf-8 -*-
"""
Punto de entrada principal para el contenedor 'api' (FastAPI).

Inicia los endpoints HTTP para Alexa y el servidor WebSocket para el Gateway.
"""
import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from api.core.config import HOST, PORT
from api.routers.alexa import router as alexa_router, set_main_event_loop
from api.routers.dispositivos import router as dispositivos_router
from api.adapters.gateway_client import (
    register_gateway_connection,
    unregister_gateway_connection,
    handle_incoming_message,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Guardar referencia del event loop principal para los handlers de Alexa
    loop = asyncio.get_running_loop()
    set_main_event_loop(loop)
    print(f"[API] Servidor HospedaSmart iniciado en {HOST}:{PORT}", flush=True)
    yield
    print("[API] Servidor HospedaSmart apagándose...", flush=True)


app = FastAPI(
    title="HospedaSmart API",
    description="Backend principal para gestión de hospedajes y automatización",
    version="0.1.0",
    lifespan=lifespan,
)

# Permitir CORS básico
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar router de Alexa
app.include_router(alexa_router)
# Control directo de dispositivos (pruebas sin Alexa y futuro panel)
app.include_router(dispositivos_router)


@app.get("/health")
async def health_check():
    """Endpoint básico para comprobar que el servicio está vivo."""
    return {"status": "ok", "service": "HospedaSmart API"}


@app.websocket("/ws/gateway")
async def websocket_gateway_endpoint(websocket: WebSocket):
    """
    Canal WebSocket bidireccional con el Gateway de hardware.
    El gateway inicia la conexión hacia este endpoint.
    """
    await websocket.accept()
    register_gateway_connection(websocket)
    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                data = json.loads(data_text)
                handle_incoming_message(data)
            except json.JSONDecodeError:
                print(f"[API-WS] Mensaje inválido recibido: {data_text}", flush=True)
    except WebSocketDisconnect:
        unregister_gateway_connection(websocket)
    except Exception as e:
        print(f"[API-WS] Error en conexión WebSocket: {e}", flush=True)
        unregister_gateway_connection(websocket)


if __name__ == "__main__":
    uvicorn.run("api.main:app", host=HOST, port=PORT, reload=False)
