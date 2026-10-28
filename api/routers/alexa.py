# -*- coding: utf-8 -*-
"""
Router de FastAPI para recibir y despachar peticiones de Alexa.

Implementa los handlers con ask-sdk-core y utiliza WebserviceSkillHandler
para procesar la solicitud sin bloquear el event loop de FastAPI.
"""
import asyncio
from typing import Awaitable, Callable
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import (
    AbstractRequestHandler,
    AbstractExceptionHandler,
    AbstractRequestInterceptor,
)
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_webservice_support.webservice_handler import WebserviceSkillHandler

from api.core.config import SKILL_ID, VERIFY_ALEXA_SIGNATURE, VERIFY_ALEXA_TIMESTAMP
from api.usecases.confort import controlar_confort
from api.usecases.acceso import controlar_puerta

router = APIRouter()
_main_event_loop: asyncio.AbstractEventLoop | None = None


def set_main_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Guarda la referencia al bucle de eventos principal de FastAPI."""
    global _main_event_loop
    _main_event_loop = loop


def _ejecutar_corutina_en_loop(coro, timeout: float = 3.5):
    """Ejecuta una corutina async en el bucle principal desde un hilo worker."""
    global _main_event_loop
    if _main_event_loop is None or not _main_event_loop.is_running():
        # Fallback si se ejecuta en el mismo hilo
        return asyncio.run(coro)
    future = asyncio.run_coroutine_threadsafe(coro, _main_event_loop)
    return future.result(timeout=timeout)


# ---------- Handlers de Alexa ----------

class LaunchRequestHandler(AbstractRequestHandler):
    """Saludo al abrir la skill: 'Alexa, abre HospedaSmart'."""

    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        texto = "Hola, bienvenido a HospedaSmart. ¿Qué deseas hacer?"
        return (
            handler_input.response_builder
            .speak(texto)
            .ask("Puedes pedirme encender o apagar el ventilador o la luz, o abrir o cerrar la puerta.")
            .response
        )


class OrdenIntentHandler(AbstractRequestHandler):
    """
    Intent que se traduce en una orden física, delegada a un caso de uso.

    Se crea una instancia por intent, p. ej. EncenderVentiladorIntent -> controlar_confort("ventilador", "encender").
    """

    def __init__(self, intent_name: str, caso_de_uso: Callable[[], Awaitable[tuple[bool, str]]]):
        self.intent_name = intent_name
        self.caso_de_uso = caso_de_uso

    def can_handle(self, handler_input):
        return is_intent_name(self.intent_name)(handler_input)

    def handle(self, handler_input):
        print(f"[ALEXA] Intent {self.intent_name}", flush=True)
        try:
            _, mensaje = _ejecutar_corutina_en_loop(self.caso_de_uso(), timeout=3.0)
        except Exception as e:
            print(f"[ALEXA-ERROR] Error al procesar caso de uso: {e}", flush=True)
            mensaje = "Hubo un retraso al comunicar con la habitación. Intenta de nuevo."

        return (
            handler_input.response_builder
            .speak(mensaje)
            .set_should_end_session(True)
            .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    """AMAZON.HelpIntent: ayuda al usuario."""

    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        texto = "Puedes decirme: enciende el ventilador, apaga la luz o abre la puerta. ¿Qué deseas hacer?"
        return handler_input.response_builder.speak(texto).ask(texto).response


class FallbackIntentHandler(AbstractRequestHandler):
    """AMAZON.FallbackIntent: frase no reconocida."""

    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        texto = ("No entendí esa orden. Puedes decir: enciende o apaga la luz, "
                 "enciende o apaga el ventilador, abre o cierra la puerta.")
        return handler_input.response_builder.speak(texto).ask(texto).response


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """AMAZON.CancelIntent y AMAZON.StopIntent: salir de la skill."""

    def can_handle(self, handler_input):
        return (
            is_intent_name("AMAZON.CancelIntent")(handler_input)
            or is_intent_name("AMAZON.StopIntent")(handler_input)
            or is_intent_name("AMAZON.NavigateHomeIntent")(handler_input)
        )

    def handle(self, handler_input):
        return (
            handler_input.response_builder
            .speak("Hasta luego.")
            .set_should_end_session(True)
            .response
        )


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Cierre de sesión de Alexa (silencio, error o salida). No se puede hablar aquí; solo se registra."""

    def can_handle(self, handler_input):
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        motivo = handler_input.request_envelope.request.reason
        print(f"[ALEXA] Sesión terminada: {motivo}", flush=True)
        return handler_input.response_builder.response


class IntentDesconocidoHandler(AbstractRequestHandler):
    """
    Captura intents no registrados. Suele significar que el modelo de la consola de Alexa
    no coincide con alexa/interaction_model.json. Va registrado al final para no tapar a los demás.
    """

    def can_handle(self, handler_input):
        return is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        nombre = handler_input.request_envelope.request.intent.name
        print(f"[ALEXA] Intent no implementado: {nombre}. Si no es de una fase futura, pega "
              "alexa/interaction_model.json en la consola de Alexa y pulsa Build Model.", flush=True)
        texto = "Esa función aún no está disponible en este módulo."
        return (
            handler_input.response_builder
            .speak(texto)
            .set_should_end_session(True)
            .response
        )


class LogRequestInterceptor(AbstractRequestInterceptor):
    """Registra en consola cada petición entrante."""

    def process(self, handler_input):
        req = handler_input.request_envelope.request
        intent = getattr(req, "intent", None)
        nombre_intent = f" -> {intent.name}" if intent is not None else ""
        print(f"[ALEXA-REQUEST] {req.object_type}{nombre_intent}", flush=True)


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Manejo de excepciones no controladas."""

    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        print(f"[ALEXA-EXCEPTION] {exception!r}", flush=True)
        texto = "Ocurrió un error inesperado al procesar la orden."
        return handler_input.response_builder.speak(texto).ask(texto).response


# ---------- Construcción de la Skill ----------

sb = SkillBuilder()
sb.skill_id = SKILL_ID

# 1. Saludo y peticiones base
sb.add_request_handler(LaunchRequestHandler())

# 2. Órdenes físicas: (intent de Alexa, caso de uso que lo atiende)
ORDENES = [
    # Flujo 1: Confort (Ventilador y Luz)
    ("EncenderVentiladorIntent", lambda: controlar_confort("ventilador", "encender")),
    ("ApagarVentiladorIntent", lambda: controlar_confort("ventilador", "apagar")),
    ("EncenderLuzIntent", lambda: controlar_confort("luz", "encender")),
    ("ApagarLuzIntent", lambda: controlar_confort("luz", "apagar")),
    # Flujo 3: Acceso (cerrojo; sin PIN todavía)
    ("AbrirPuertaIntent", lambda: controlar_puerta("abrir")),
    ("CerrarPuertaIntent", lambda: controlar_puerta("cerrar")),
]
for intent_name, caso_de_uso in ORDENES:
    sb.add_request_handler(OrdenIntentHandler(intent_name, caso_de_uso))

# 3. Handlers estándar y salvaguardas
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentDesconocidoHandler())  # siempre el último

sb.add_global_request_interceptor(LogRequestInterceptor())
sb.add_exception_handler(CatchAllExceptionHandler())

skill_instance = sb.create()
alexa_handler = WebserviceSkillHandler(
    skill=skill_instance,
    verify_signature=VERIFY_ALEXA_SIGNATURE,
    verify_timestamp=VERIFY_ALEXA_TIMESTAMP
)


# ---------- Endpoint HTTP ----------

@router.post("/alexa")
async def handle_alexa_post(request: Request):
    """Recibe la llamada POST HTTPS de Alexa (o el simulador de pruebas)."""
    headers = dict(request.headers)
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8")

    try:
        respuesta_json = await run_in_threadpool(
            alexa_handler.verify_request_and_dispatch,
            headers,
            body_str
        )
    except Exception as exc:
        print(f"[ALEXA-VERIFY-ERROR] Error al verificar petición: {exc}", flush=True)
        raise HTTPException(status_code=400, detail="Petición de Alexa no válida")

    if isinstance(respuesta_json, dict):
        return JSONResponse(content=respuesta_json)
    return Response(content=respuesta_json, media_type="application/json")
