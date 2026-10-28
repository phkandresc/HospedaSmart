# -*- coding: utf-8 -*-
"""
Caso de uso: Confort (Flujo 1 - Ventilador y Luz).

Contiene la regla de negocio para encender y apagar dispositivos de confort.
No depende de cómo se recibió la orden (Alexa, web, etc.) ni de cómo se habla
con el microcontrolador (serie, mqtt, etc.).
"""
from api.adapters.gateway_client import enviar_comando_dispositivo


async def controlar_confort(dispositivo: str, accion: str) -> tuple[bool, str]:
    """
    Controla un dispositivo de confort de la habitación.

    :param dispositivo: 'ventilador' o 'luz'
    :param accion: 'encender' o 'apagar'
    :return: (exito: bool, mensaje_respuesta: str)
    """
    dispositivo_normalizado = dispositivo.lower().strip()
    accion_normalizada = accion.lower().strip()

    if dispositivo_normalizado not in ("ventilador", "luz"):
        return False, f"El dispositivo '{dispositivo}' no es válido para confort."

    target_device = "room101.fan" if dispositivo_normalizado == "ventilador" else "room101.light"
    power_on = (accion_normalizada == "encender")

    ok = await enviar_comando_dispositivo(
        device=target_device,
        action="set_power",
        params={"on": power_on},
        timeout_s=2.5
    )

    if ok:
        if dispositivo_normalizado == "ventilador":
            estado = "encendido" if power_on else "apagado"
            return True, f"Listo, ventilador {estado}."
        else:
            estado = "encendida" if power_on else "apagada"
            return True, f"Listo, luz {estado}."
    else:
        return False, (
            "No pude comunicarme con la habitación. "
            "Verifica que el gateway y el hardware estén conectados."
        )
