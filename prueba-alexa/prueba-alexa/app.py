# -*- coding: utf-8 -*-
"""
HospedaSmart - Endpoint propio para una custom skill de Alexa (es-US).

Flujo: Alexa -> ngrok (HTTPS) -> este servidor Flask (puerto 5000, ruta "/")
       -> ask-sdk elige el handler adecuado -> orden por USB (pyserial) al Arduino
       -> respuesta JSON de vuelta a Alexa.
"""
import threading
import time

import serial
from serial.tools import list_ports
from flask import Flask
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import (
    AbstractRequestHandler,
    AbstractExceptionHandler,
    AbstractRequestInterceptor,
)
from ask_sdk_core.utils import is_request_type, is_intent_name
from flask_ask_sdk.skill_adapter import SkillAdapter

# Pega aquí el Skill ID de la consola de Alexa (amzn1.ask.skill....).
# Si lo dejas en None, el servidor acepta peticiones de cualquier skill.
SKILL_ID = None

# Puerto del Arduino (por ejemplo "COM3"). Con None se busca solo el único
# puerto USB conectado (se ignoran los puertos Bluetooth).
SERIAL_PORT = None
BAUDRATE = 115200  # Debe coincidir con Serial.begin() del sketch.


# ---------- Conexión con el Arduino (pyserial) ----------

def detectar_puerto():
    """Devuelve el único puerto serie USB conectado, o lanza un error."""
    usb = [p.device for p in list_ports.comports() if p.hwid.startswith("USB")]
    if len(usb) == 1:
        return usb[0]
    if not usb:
        raise serial.SerialException("No se encontró ningún Arduino por USB.")
    raise serial.SerialException(
        f"Hay varios puertos USB ({', '.join(usb)}); define SERIAL_PORT.")


class Arduino:
    """Mantiene abierto el puerto serie y envía órdenes de una en una.

    El sketch responde "OK:<orden>" cuando la ejecuta; cualquier otra línea
    (menús, avisos) se muestra en consola y se ignora.
    """

    def __init__(self, puerto, baudios):
        self._puerto = puerto
        self._baudios = baudios
        self._serial = None
        self._lock = threading.Lock()  # Flask atiende peticiones en hilos

    def _abrir(self):
        puerto = self._puerto or detectar_puerto()
        self._serial = serial.Serial(puerto, self._baudios, timeout=0.5)
        # Abrir el puerto reinicia el Arduino: se espera a que termine setup().
        time.sleep(2.5)
        self._serial.reset_input_buffer()
        print(f"[SERIAL] Conectado a {puerto} a {self._baudios} baudios", flush=True)

    def _cerrar(self):
        if self._serial is not None:
            try:
                self._serial.close()
            except serial.SerialException:
                pass
        self._serial = None

    def conectar(self):
        """Abre el puerto al arrancar; si falla se reintenta con la primera orden."""
        with self._lock:
            try:
                self._abrir()
            except serial.SerialException as e:
                print(f"[SERIAL] Sin conexión todavía: {e}", flush=True)

    def enviar(self, orden, espera=3.0):
        """Envía la orden y devuelve True si el Arduino la confirmó a tiempo."""
        with self._lock:
            try:
                if self._serial is None:
                    self._abrir()
                self._serial.reset_input_buffer()
                self._serial.write((orden + "\n").encode("ascii"))
                print(f"[SERIAL] -> {orden}", flush=True)

                limite = time.monotonic() + espera
                while time.monotonic() < limite:
                    linea = self._serial.readline().decode("utf-8", "replace").strip()
                    if not linea:
                        continue
                    print(f"[ARDUINO] {linea}", flush=True)
                    if linea == f"OK:{orden}":
                        return True
                print(f"[SERIAL] Sin confirmación para {orden}", flush=True)
                return False
            except serial.SerialException as e:
                # Cable desconectado o puerto ocupado: se reabre en la siguiente orden.
                print(f"[SERIAL] Error: {e}", flush=True)
                self._cerrar()
                return False


arduino = Arduino(SERIAL_PORT, BAUDRATE)


# ---------- Handlers de peticiones ----------

class LaunchRequestHandler(AbstractRequestHandler):
    """Se ejecuta al decir: 'Alexa, abre HospedaSmart'."""

    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        texto = "Hola, soy HospedaSmart desde tu computadora. ¿Qué deseas hacer?"
        return (
            handler_input.response_builder
            .speak(texto)
            .ask("¿Qué deseas hacer?")  # .ask() deja la sesión abierta
            .response
        )


class OrdenArduinoIntentHandler(AbstractRequestHandler):
    """Intent que se traduce en una orden física para el Arduino.

    Se crea una instancia por intent, p. ej. EncenderVentiladorIntent -> VENT_ON.
    """

    def __init__(self, intent, orden, texto_ok):
        self.intent = intent
        self.orden = orden
        self.texto_ok = texto_ok

    def can_handle(self, handler_input):
        return is_intent_name(self.intent)(handler_input)

    def handle(self, handler_input):
        print(f"[ORDEN] {self.intent} -> {self.orden}", flush=True)
        if arduino.enviar(self.orden):
            texto = self.texto_ok
        else:
            texto = ("No pude comunicarme con la casa. "
                     "Revisa que el Arduino esté conectado por USB.")
        return (
            handler_input.response_builder
            .speak(texto)
            .set_should_end_session(True)
            .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    """AMAZON.HelpIntent: el usuario pide ayuda."""

    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        texto = ("Puedes decirme: enciende el ventilador, apaga la luz "
                 "o abre la puerta. ¿Qué deseas hacer?")
        return handler_input.response_builder.speak(texto).ask(texto).response


class FallbackIntentHandler(AbstractRequestHandler):
    """AMAZON.FallbackIntent: la frase no coincide con ninguna orden."""

    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        texto = ("No entendí esa orden. Puedes decir: enciende o apaga la luz, "
                 "enciende o apaga el ventilador, abre o cierra la puerta.")
        return handler_input.response_builder.speak(texto).ask(texto).response


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """AMAZON.CancelIntent, StopIntent y NavigateHomeIntent: el usuario quiere salir."""

    def can_handle(self, handler_input):
        return (is_intent_name("AMAZON.CancelIntent")(handler_input)
                or is_intent_name("AMAZON.StopIntent")(handler_input)
                or is_intent_name("AMAZON.NavigateHomeIntent")(handler_input))

    def handle(self, handler_input):
        return (
            handler_input.response_builder
            .speak("Hasta luego.")
            .set_should_end_session(True)
            .response
        )


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Alexa avisa que la sesión terminó (silencio, error o salida).
    No se puede hablar en esta respuesta; solo se registra."""

    def can_handle(self, handler_input):
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        motivo = handler_input.request_envelope.request.reason
        print(f"[SESION] Terminada: {motivo}", flush=True)
        return handler_input.response_builder.response


class IntentDesconocidoHandler(AbstractRequestHandler):
    """Intent que este servidor no conoce (p. ej. HelloWorldIntent de la plantilla).

    Significa que el modelo de la consola de Alexa no coincide con
    interaction_model.json. Va registrado al final para no tapar a los demás.
    """

    def can_handle(self, handler_input):
        return is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        nombre = handler_input.request_envelope.request.intent.name
        print(f"[AVISO] Intent desconocido: {nombre}. Pega interaction_model.json "
              "en la consola de Alexa y pulsa Build Model.", flush=True)
        texto = ("Esa orden no está configurada en la skill. Actualiza el modelo "
                 "de interacción en la consola de Alexa.")
        return (
            handler_input.response_builder
            .speak(texto)
            .set_should_end_session(True)
            .response
        )


# ---------- Registro de cada petición ----------

class LogRequestInterceptor(AbstractRequestInterceptor):
    """Muestra en consola el tipo de petición y el intent que eligió Alexa."""

    def process(self, handler_input):
        request = handler_input.request_envelope.request
        intent = getattr(request, "intent", None)
        detalle = f" -> {intent.name}" if intent is not None else ""
        print(f"[ALEXA] {request.object_type}{detalle}", flush=True)


# ---------- Manejador de excepciones ----------

class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Atrapa cualquier error (o intent sin handler) y responde en español."""

    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        print(f"[ERROR] {exception!r}", flush=True)
        texto = "Lo siento, hubo un problema. Intenta de nuevo, por favor."
        return handler_input.response_builder.speak(texto).ask(texto).response


# ---------- Registro de handlers en la skill ----------

# (intent de Alexa, orden del sketch, lo que responde Alexa)
ORDENES = [
    ("EncenderVentiladorIntent", "VENT_ON", "Listo, ventilador encendido"),
    ("ApagarVentiladorIntent", "VENT_OFF", "Listo, ventilador apagado"),
    ("EncenderLuzIntent", "LUZ_ON", "Listo, luz encendida"),
    ("ApagarLuzIntent", "LUZ_OFF", "Listo, luz apagada"),
    ("AbrirPuertaIntent", "PUERTA_ABRIR", "Listo, puerta abierta"),
    ("CerrarPuertaIntent", "PUERTA_CERRAR", "Listo, puerta cerrada"),
]

sb = SkillBuilder()
sb.skill_id = SKILL_ID
sb.add_request_handler(LaunchRequestHandler())
for intent, orden, texto_ok in ORDENES:
    sb.add_request_handler(OrdenArduinoIntentHandler(intent, orden, texto_ok))
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentDesconocidoHandler())  # siempre el último
sb.add_global_request_interceptor(LogRequestInterceptor())
sb.add_exception_handler(CatchAllExceptionHandler())


# ---------- Servidor web Flask ----------

app = Flask(__name__)

# Seguridad: con estas dos opciones en True (valor por defecto, aquí
# explícito) se rechaza cualquier petición que no venga firmada por Amazon
# o cuyo timestamp tenga más de 150 segundos de antigüedad.
app.config["ASK_SDK_VERIFY_SIGNATURE"] = True
app.config["ASK_SDK_VERIFY_TIMESTAMP"] = True

# SkillAdapter conecta Flask con ask-sdk.
skill_adapter = SkillAdapter(skill=sb.create(), skill_id=SKILL_ID, app=app)


@app.route("/", methods=["POST"])
def invoke_skill():
    return skill_adapter.dispatch_request()


if __name__ == "__main__":
    arduino.conectar()
    # ngrok reenvía https://xxxx.ngrok-free.app -> http://localhost:5000
    app.run(host="0.0.0.0", port=5000)
