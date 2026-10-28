# -*- coding: utf-8 -*-
"""
Caso de uso: Acceso (Flujo 3 - Cerrojo de la puerta).

Por ahora abre y cierra el cerrojo directamente, igual que la prueba de concepto
original. El flujo F3 completo añadirá aquí verificar_pin() (credencial vigente +
hash del PIN) y el registro del AccessEvent antes de abrir.
"""
from api.adapters.gateway_client import enviar_comando_dispositivo


async def controlar_puerta(accion: str) -> tuple[bool, str]:
    """
    Abre o cierra el cerrojo de la habitación.

    :param accion: 'abrir' o 'cerrar'
    :return: (exito: bool, mensaje_respuesta: str)
    """
    accion_normalizada = accion.lower().strip()
    if accion_normalizada not in ("abrir", "cerrar"):
        return False, f"La acción '{accion}' no es válida para la puerta."

    # TODO F3: exigir verificar_pin(room_id, pin) antes de abrir y registrar el acceso
    cerrar = (accion_normalizada == "cerrar")

    ok = await enviar_comando_dispositivo(
        device="room101.lock",
        action="set_locked",
        params={"locked": cerrar},
        timeout_s=2.5
    )

    if ok:
        return True, "Listo, puerta cerrada." if cerrar else "Listo, puerta abierta."
    return False, (
        "No pude comunicarme con la habitación. "
        "Verifica que el gateway y el hardware estén conectados."
    )
