# -*- coding: utf-8 -*-
"""
Router de FastAPI para recibir y despachar peticiones de Alexa.

Implementa los handlers con ask-sdk-core y utiliza WebserviceSkillHandler
para procesar la solicitud sin bloquear el event loop de FastAPI.
"""
import asyncio
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
            .ask("Puedes pedirme encender o apagar el ventilador o la luz.")
            .response
        )


class ConfortIntentHandler(AbstractRequestHandler):
    """Maneja intents de confort (ventilador y luz)."""

    def __init__(self, intent_name: str, dispositivo: str, accion: str):
        self.intent_name = intent_name
        self.dispositivo = dispositivo
        self.accion = accion

    def can_handle(self, handler_input):
        return is_intent_name(self.intent_name)(handler_input)

    def handle(self, handler_input):
        print(f"[ALEXA] Intent {self.intent_name} -> {self.dispositivo} {self.accion}", flush=True)
        try:
            _, mensaje = _ejecutar_corutina_en_loop(
                controlar_confort(self.dispositivo, self.accion),
                timeout=3.0
            )
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
        texto = "Puedes decirme: enciende el ventilador, apaga el ventilador, enciende la luz o apaga la luz."
        return handler_input.response_builder.speak(texto).ask(texto).response


class FallbackIntentHandler(AbstractRequestHandler):
    """AMAZON.FallbackIntent: frase no reconocida."""

    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        texto = "No entendí esa orden. Puedes pedirme controlar el ventilador o la luz de la habitación."
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
    """Cierre de sesión de Alexa."""

    def can_handle(self, handler_input):
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        return handler_input.response_builder.response


class IntentDesconocidoHandler(AbstractRequestHandler):
    """Captura intents no registrados (ej. cuando falta sincronizar interaction_model)."""

    def can_handle(self, handler_input):
        return is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        nombre = handler_input.request_envelope.request.intent.name
        print(f"[ALEXA] Intent no implementado en esta fase: {nombre}", flush=True)
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

# 2. Flujo 1: Confort (Ventilador y Luz)
sb.add_request_handler(ConfortIntentHandler("EncenderVentiladorIntent", "ventilador", "encender"))
sb.add_request_handler(ConfortIntentHandler("ApagarVentiladorIntent", "ventilador", "apagar"))
sb.add_request_handler(ConfortIntentHandler("EncenderLuzIntent", "luz", "encender"))
sb.add_request_handler(ConfortIntentHandler("ApagarLuzIntent", "luz", "apagar"))

# 3. Handlers estándar y salvaguardas
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentDesconocidoHandler())

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
