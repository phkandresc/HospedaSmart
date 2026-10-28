# -*- coding: utf-8 -*-
"""
Router HTTP para controlar dispositivos sin pasar por Alexa.

Sirve para probar la cadena PC → API → Gateway → Arduino desde el navegador
(http://localhost:8000/docs) o con un script, usando el mismo caso de uso que Alexa.
Más adelante lo usará también el panel web.
"""
from typing import Literal
from fastapi import APIRouter, HTTPException

from api.adapters.gateway_client import gateway_conectado
from api.usecases.confort import controlar_confort
from api.usecases.acceso import controlar_puerta

router = APIRouter(prefix="/dispositivos", tags=["dispositivos"])


@router.get("/estado")
async def estado_gateway():
    """Indica si el gateway de la habitación está conectado a la API."""
    return {"gateway_conectado": gateway_conectado()}


@router.post("/puerta/{accion}")
async def controlar_cerrojo(accion: Literal["abrir", "cerrar"]):
    """Abre o cierra el cerrojo y espera la confirmación del Arduino."""
    ok, mensaje = await controlar_puerta(accion)
    if not ok:
        raise HTTPException(status_code=504, detail=mensaje)
    return {"ok": True, "mensaje": mensaje}


@router.post("/{dispositivo}/{accion}")
async def controlar_dispositivo(
    dispositivo: Literal["ventilador", "luz"],
    accion: Literal["encender", "apagar"],
):
    """Enciende o apaga el ventilador o la luz y espera la confirmación del Arduino."""
    ok, mensaje = await controlar_confort(dispositivo, accion)
    if not ok:
        # 504: la orden salió pero nadie la confirmó a tiempo (gateway o Arduino)
        raise HTTPException(status_code=504, detail=mensaje)
    return {"ok": True, "mensaje": mensaje}
