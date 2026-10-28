# -*- coding: utf-8 -*-
"""
Script de prueba local para simular peticiones de Alexa hacia la API.

Permite probar el flujo completo (Alexa -> FastAPI -> usecases -> gateway_client)
sin necesidad de ngrok, Echo Dot ni conexión a internet.
"""
import sys
import uuid
import datetime
import httpx

API_URL = "http://localhost:8000/alexa"


def build_alexa_payload(request_type: str, intent_name: str | None = None) -> dict:
    """Construye un payload JSON idéntico al que envía Amazon Alexa."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    req_id = f"amzn1.echo-api.request.{uuid.uuid4()}"
    sess_id = f"amzn1.echo-api.session.{uuid.uuid4()}"

    payload = {
        "version": "1.0",
        "session": {
            "new": (request_type == "LaunchRequest"),
            "sessionId": sess_id,
            "application": {"applicationId": "amzn1.ask.skill.simulada"},
            "user": {"userId": "amzn1.ask.account.usuario_prueba"}
        },
        "context": {
            "System": {
                "application": {"applicationId": "amzn1.ask.skill.simulada"},
                "user": {"userId": "amzn1.ask.account.usuario_prueba"},
                "device": {"deviceId": "device_prueba_simulado"}
            }
        },
        "request": {
            "type": request_type,
            "requestId": req_id,
            "timestamp": now_iso,
            "locale": "es-US"
        }
    }

    if intent_name:
        payload["request"]["intent"] = {
            "name": intent_name,
            "confirmationStatus": "NONE"
        }

    return payload


def enviar_peticion(nombre_prueba: str, request_type: str, intent_name: str | None = None):
    print(f"\n==================================================")
    print(f"Probando: {nombre_prueba}")
    print(f"==================================================")
    payload = build_alexa_payload(request_type, intent_name)

    try:
        with httpx.Client(timeout=6.0) as client:
            resp = client.post(API_URL, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                speech = (
                    data.get("response", {})
                    .get("outputSpeech", {})
                    .get("ssml", "")
                )
                # Limpiar etiquetas <speak> para mostrarlo limpio
                texto_limpio = speech.replace("<speak>", "").replace("</speak>", "").strip()
                print(f"-> Código HTTP: {resp.status_code} OK")
                print(f"-> 🗣️ Alexa dice: \"{texto_limpio}\"")
                return True
            else:
                print(f"-> ❌ Error HTTP {resp.status_code}: {resp.text}")
                return False
    except httpx.ConnectError:
        print("-> ❌ Error: No se pudo conectar a http://localhost:8000.")
        print("   Asegúrate de que la API esté corriendo (python -m api.main).")
        return False
    except Exception as e:
        print(f"-> ❌ Excepción: {e}")
        return False


def main():
    print("Simulador de Peticiones de Alexa - HospedaSmart")
    print("-----------------------------------------------")
    if len(sys.argv) > 1:
        opcion = sys.argv[1]
    else:
        print("1. Saludo inicial (LaunchRequest)")
        print("2. 'Alexa, enciende el ventilador' (EncenderVentiladorIntent)")
        print("3. 'Alexa, apaga el ventilador' (ApagarVentiladorIntent)")
        print("4. 'Alexa, enciende la luz' (EncenderLuzIntent)")
        print("5. 'Alexa, apaga la luz' (ApagarLuzIntent)")
        print("6. 'Alexa, abre la puerta' (AbrirPuertaIntent)")
        print("7. 'Alexa, cierra la puerta' (CerrarPuertaIntent)")
        print("8. Ejecutar todas en secuencia")
        opcion = input("Elige una opción (1-8): ").strip()

    pruebas = {
        "1": ("LaunchRequest", "LaunchRequest", None),
        "2": ("Encender Ventilador", "IntentRequest", "EncenderVentiladorIntent"),
        "3": ("Apagar Ventilador", "IntentRequest", "ApagarVentiladorIntent"),
        "4": ("Encender Luz", "IntentRequest", "EncenderLuzIntent"),
        "5": ("Apagar Luz", "IntentRequest", "ApagarLuzIntent"),
        "6": ("Abrir Puerta", "IntentRequest", "AbrirPuertaIntent"),
        "7": ("Cerrar Puerta", "IntentRequest", "CerrarPuertaIntent"),
    }

    if opcion == "8":
        for k in sorted(pruebas.keys()):
            nombre, req_type, intent = pruebas[k]
            enviar_peticion(nombre, req_type, intent)
    elif opcion in pruebas:
        nombre, req_type, intent = pruebas[opcion]
        enviar_peticion(nombre, req_type, intent)
    else:
        print("Opción no válida.")


if __name__ == "__main__":
    main()
