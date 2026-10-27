# Análisis de `prueba-alexa/` — prueba de factibilidad del canal de voz

> Documento de lectura rápida. Resume qué hay en la carpeta, cómo funciona y qué conclusiones
> sirven para planificar la arquitectura definitiva.
>
> **Fecha:** 2026-10-27 · **Naturaleza:** *spike* / prueba de concepto, **no** un MVP.

---

## 1. Qué demuestra esta prueba

Que una persona puede hablarle a un Echo Dot y que esa orden termine accionando hardware físico
en una habitación, usando **infraestructura propia y gratuita** (sin AWS Lambda, sin IoT Core).

El objetivo era responder una sola pregunta: *"¿es viable conectar voz → backend propio → Arduino?"*.
La respuesta es **sí**, con matices de despliegue que se detallan en la sección 6.

---

## 2. Estructura de la carpeta

```
prueba-alexa/
├── README-conexion puente alexa.md     ← guía del puente Alexa ↔ backend (187 líneas)
└── prueba-alexa/                       ← carpeta anidada con el mismo nombre (ver §7)
    ├── app.py                          ← servidor Flask + skill de Alexa (313 líneas)
    ├── requirements.txt                ← 4 dependencias con versión fija
    ├── interaction_model.json          ← modelo de interacción de la consola de Alexa
    ├── README.md                       ← guía técnica del servidor
    ├── sensor_diagnostics/
    │   └── sensor_diagnostics.ino      ← banco de pruebas del kit (925 líneas)
    ├── venv/                           ← entorno virtual Windows · 55 MB · NO debe versionarse
    └── __pycache__/                    ← caché de Python · NO debe versionarse
```

---

## 3. Arquitectura de la prueba

```
 Persona ──voz──▶ Echo Dot ──▶ Nube Alexa ──HTTPS/JSON──▶ ngrok ──▶ Flask :5000
                                                                       │
                                                                       │ USB serie 115200
                                                                       ▼
                                                          Arduino UNO + KS0085
                                                          (servo, relé, LEDs, buzzer…)
```

**El truco central:** la nube de Alexa necesita una URL HTTPS pública. La PC del grupo está
detrás de un router doméstico, sin IP pública. **ngrok** abre un túnel y le da una URL
`https://<algo>.ngrok-free.dev` que reenvía al `http://localhost:5000` local.

### Piezas y responsabilidades

| Pieza | Rol |
|---|---|
| **Echo Dot (3.ª gen.)** | Captura la voz, reproduce la respuesta |
| **Nube de Alexa** | Transcribe, clasifica la frase en un *intent* y hace `POST /` al endpoint |
| **Skill "Custom"** | Define nombre de invocación, intents y frases de ejemplo |
| **ngrok** | Publica el puerto local con HTTPS válido |
| **`app.py`** | Recibe el intent, traduce a una orden de texto y la manda por serie |
| **`sensor_diagnostics.ino`** | Ejecuta la orden física y confirma con `OK:<orden>` |

---

## 4. Los tres archivos de software, en detalle

### 4.1 `app.py` — el puente

Tecnologías: **Flask** (servidor HTTP) + **ask-sdk-core** (SDK oficial de Alexa) +
**flask-ask-sdk** (pegamento entre ambos) + **pyserial** (USB serie).

**Dos capas bien separadas:**

1. **Capa Alexa** — clases que heredan de `AbstractRequestHandler`:
   - `LaunchRequestHandler`: saludo inicial, deja la sesión abierta (`.ask()`).
   - `OrdenArduinoIntentHandler`: **genérico y reutilizable**. Se instancia una vez por intent
     con `(nombre_intent, orden_física, frase_de_respuesta)`. Toda la tabla de órdenes está
     declarada en una lista `ORDENES`, así que agregar un comando = agregar **una línea**:
     ```python
     ("EncenderVentiladorIntent", "VENT_ON", "Listo, ventilador encendido")
     ```
   - `HelpIntentHandler`, `FallbackIntentHandler`, `CancelOrStopIntentHandler`,
     `SessionEndedRequestHandler`.
   - `IntentDesconocidoHandler`: red de seguridad que avisa si la consola de Alexa tiene un
     modelo distinto al del repo. **Registrado al final a propósito** (el orden importa: el
     primero que responde `can_handle = True` gana).
   - `LogRequestInterceptor`: imprime cada petición y el intent elegido. Es la herramienta
     principal de depuración.
   - `CatchAllExceptionHandler`: responde en español ante cualquier excepción.

2. **Capa hardware** — clase `Arduino`:
   - **Detección automática** del puerto: si hay exactamente un dispositivo USB conectado lo usa;
     si hay 0 o varios, falla con un mensaje claro (`SERIAL_PORT` permite fijarlo a mano).
   - **`threading.Lock`**: Flask atiende peticiones en hilos y el puerto serie solo admite un
     escritor. Sin el lock, dos órdenes simultáneas corromperían la comunicación.
   - **Espera de 2,5 s al abrir el puerto**: abrir el serie **reinicia** el Arduino (comportamiento
     del hardware, no del código), así que hay que dejarlo arrancar.
   - **Protocolo de confirmación**: envía `VENT_ON\n` y espera hasta 3 s a leer la línea
     `OK:VENT_ON`. Si no llega, responde a Alexa "no pude comunicarme con la casa".
     Esto convierte un `print` ciego en un **acuse real de ejecución**.
   - **Recuperación**: si el cable se desconecta, cierra el puerto y lo reabre en la siguiente orden.

**Seguridad activada:** `ASK_SDK_VERIFY_SIGNATURE` y `ASK_SDK_VERIFY_TIMESTAMP` en `True`.
Cualquier `curl` o Postman recibe **HTTP 400**: solo Amazon puede invocar el endpoint.
Es la práctica correcta y conviene conservarla en la versión final.

### 4.2 `interaction_model.json` — el "diccionario" de frases

Define el nombre de invocación `hospeda smart`, el locale `es-US` y **6 intents** propios:

| Intent | Orden enviada | Frases de ejemplo (resumido) |
|---|---|---|
| `EncenderVentiladorIntent` | `VENT_ON` | enciende / prende / activa el ventilador |
| `ApagarVentiladorIntent` | `VENT_OFF` | apaga / desactiva / detén el ventilador |
| `EncenderLuzIntent` | `LUZ_ON` | enciende la luz / el foco |
| `ApagarLuzIntent` | `LUZ_OFF` | apaga la luz / el foco |
| `AbrirPuertaIntent` | `PUERTA_ABRIR` | abre la puerta / desbloquea el cerrojo |
| `CerrarPuertaIntent` | `PUERTA_CERRAR` | cierra la puerta / bloquea el cerrojo |

Más 5 intents integrados de Amazon (`Help`, `Stop`, `Cancel`, `Fallback`, `NavigateHome`).
Cada intent incluye variantes en **imperativo, subjuntivo e infinitivo** — necesario porque
Alexa no normaliza conjugaciones y "que **encienda** la luz" debe caer en el mismo intent.

> ⚠️ Este JSON **no se sincroniza solo**: hay que pegarlo en *Interaction Model → JSON Editor*
> y pulsar **Save → Build Model** cada vez que cambie. Es una fuente habitual de errores.

### 4.3 `sensor_diagnostics.ino` — el banco de pruebas del kit

No es la lógica del producto: es un **programa de diagnóstico** que ejercita el 100 % del
Keyestudio KS0085 y, además, acepta las órdenes remotas de Alexa.

**Mapa de pines:** PIR → D2 · buzzer → D3 · botón → D4 · ventilador L9110 → D5/D6 · relé → D7 ·
servo (cerrojo) → D9 · LED amarillo → D12 · LED blanco → D13 · LDR → A0 · vapor → A1 ·
MQ-2 → A2 · LCD 1602 I2C → A4/A5.

**Menú por Monitor Serial (115200 baudios):**

| Grupo | Opciones |
|---|---|
| Automático | `A` auto-test completo de fábrica |
| Actuadores | `1` servo · `2` ventilador L9110 · `3` buzzer · `4` LEDs · `5` relé · `6` LCD |
| Sensores | `7` lectura puntual · `8` telemetría continua · `9` Serial Plotter · `C` calibración ADC · `B` botón · `P` PIR · `I` escaneo I²C |
| Escenarios | `S1` acceso con PIN · `S2` emergencia de gas · `S3` confort nocturno |
| Remoto | `VENT_ON`, `VENT_OFF`, `LUZ_ON`, `LUZ_OFF`, `PUERTA_ABRIR`, `PUERTA_CERRAR` |

**Los tres escenarios simulados** — valiosos porque son la semilla de los casos de uso reales:

- **`S1` Control de acceso:** pide un PIN por consola; `1234` → abre el servo 90°, melodía de
  bienvenida, LCD "Acceso Válido", cierra a los 5 s. PIN erróneo → buzzer grave + "Acceso Denegado".
- **`S2` Emergencia de gas:** durante 6 s activa extractor al 100 %, sirena (buzzer) y alarma
  luminosa estroboscópica, con mensaje "EVACUAR EL ÁREA". Luego normaliza todo.
  **Corre localmente, sin Alexa ni internet** — decisión correcta: una emergencia no puede
  depender de la nube.
- **`S3` Confort nocturno:** lee el LDR; si `< 400` (noche) enciende la luz de cortesía unos
  segundos; si hay luz de día, no enciende nada (ahorro energético).

**Detalles de robustez que vale la pena replicar:** detecta la LCD en `0x27` **o** `0x3F` y
continúa sin ella si no está; usa `F()` para no consumir RAM; distingue "tests" (dejan el
actuador en un estado final) de "órdenes remotas" (dejan el estado pedido y responden `OK:`).

---

## 5. Flujo completo de una orden (ejemplo real)

```
1. "Alexa, pídele a hospeda smart que encienda el ventilador"
2. Alexa transcribe y resuelve el intent EncenderVentiladorIntent
3. POST https://xxxx.ngrok-free.dev/  { JSON firmado }
4. ask-sdk valida firma + timestamp
5. LogRequestInterceptor imprime  [ALEXA] IntentRequest -> EncenderVentiladorIntent
6. OrdenArduinoIntentHandler imprime  [ORDEN] EncenderVentiladorIntent -> VENT_ON
7. Arduino.enviar("VENT_ON") escribe por serie y espera confirmación
8. Sketch: D5=HIGH, D6=LOW, LCD "Ventilador ON", responde "OK:VENT_ON"
9. Servidor: Alexa dice "Listo, ventilador encendido" y cierra sesión
```

---

## 6. Limitaciones y hallazgos (lo importante para la arquitectura)

### 🔴 Bloqueantes si se toma como diseño definitivo

1. **La PC es el servidor.** Debe estar encendida, con `app.py` y ngrok corriendo. Si se apaga,
   la skill deja de responder. No es desplegable en un hospedaje real.
2. **Un solo Arduino por PC.** El puerto serie es exclusivo: no hay forma de atender dos
   habitaciones desde el mismo equipo con este esquema.
3. **El Monitor Serial del IDE y `app.py` compiten por el puerto COM.** Solo uno puede tenerlo.
4. **Órdenes de texto acopladas al sketch.** `VENT_ON` está hardcodeado en `app.py` y en el `.ino`.
   Cualquier cambio de protocolo obliga a reflashear el Arduino.

### 🟡 Limitaciones aceptables para una prueba, a resolver en la versión final

5. **La URL de ngrok cambia** (plan gratuito) → hay que reconfigurar el endpoint en la consola de
   Alexa cada vez. *(Los dos README se contradicen en esto: uno dice "dominio fijo por cuenta",
   el otro "cambia cada vez que lo reinicias". La versión correcta es la segunda.)*
6. **Latencia:** la orden espera hasta 3 s la confirmación del Arduino, dentro del tiempo que
   Alexa tolera (~8 s). Funciona, pero deja poco margen si se agregan pasos.
7. **Concurrencia serializada:** el lock garantiza integridad pero serializa todas las órdenes.
   Con un solo usuario está bien; con varios, es un cuello de botella.
8. **`SKILL_ID = None`** → el servidor acepta peticiones firmadas de *cualquier* skill. Poner el
   ID real es una línea y cierra ese hueco.
9. **Sin telemetría de vuelta:** los sensores solo se leen en el Monitor Serial. El backend nunca
   sabe si hay gas, si la puerta está abierta o cuánta luz hay. Ese es exactamente el **hito 3**
   pendiente (y el salto de "prueba" a "producto").

### 🔵 Decisiones acertadas que conviene conservar

- Verificación de firma y timestamp activada desde el principio.
- Protocolo con acuse (`OK:<orden>`) en vez de escritura ciega.
- Seguridad de emergencia **local** (S2), sin dependencia de nube.
- Instancia genérica de handler + tabla de órdenes: agregar comandos es trivial.
- Dependencias con versión fija en `requirements.txt`.
- Detectores tolerantes a fallos (LCD ausente, puerto ausente, varios puertos).

---

## 7. Inconsistencias detectadas entre los documentos

| # | Problema | Dónde | Corrección sugerida |
|---|---|---|---|
| 1 | Nombre de invocación `casa smart` vs `hospeda smart` | `README-conexion…md` §4/§9 vs `interaction_model.json` | Unificar en `hospeda smart` (el README ya lo reconoce como valor final) |
| 2 | Baud rate `9600` vs `115200` | `README-conexion…md` §1 vs `app.py` / `.ino` | El real es **115200** |
| 3 | Ruta de `sensor_diagnostics.ino` | `prueba-alexa/README.md` lo lista en la raíz; está en `sensor_diagnostics/` | Corregir la tabla |
| 4 | "`venv/` no se sube al repositorio" | `prueba-alexa/README.md` | Cierto en intención, pero **falta `.gitignore`** → hoy se subiría |
| 5 | Carpeta anidada `prueba-alexa/prueba-alexa/` | estructura | Aplanar a `prueba-alexa/{app.py,…}` |
| 6 | Rutas absolutas `C:\Users\eduar\Desktop\…` | ambos README | Usar rutas relativas |

---

## 8. Qué significa esto para la arquitectura futura

La prueba valida tres cosas y deja abiertas otras tres.

**Validado ✅**
- El canal de voz funciona con infraestructura propia y costo cero.
- El patrón *intent → orden → acuse de recibo* es sólido.
- Las emergencias deben resolverse en el borde (local), no en la nube.

**A decidir 🧭**
1. **Dónde vive la lógica de negocio.** Hoy está repartida entre el sketch y los handlers.
   La arquitectura necesita una capa intermedia (API + dominio) y dejar el firmware como
   simple ejecutor de comandos.
2. **Cómo se habla con el hardware.** USB serie sirve para una maqueta, no para N habitaciones.
   Los candidatos naturales son **MQTT** (ESP32/WiFi) o un **gateway local** que traduzca
   MQTT ↔ serie para el kit actual. Esto también resuelve la telemetría (hito 3).
3. **Dónde corre el backend.** Mover la lógica a la nube y dejar en el sitio solo el gateway,
   para que la PC del grupo deje de ser un punto único de falla.

**Regla práctica:** conservar el *contrato* (nombres de orden, acuse `OK:`) y cambiar solo el
transporte, permite reutilizar el sketch casi tal cual mientras se construye la arquitectura real.

---

## 9. Cómo se ejecuta hoy (para reproducir la prueba)

Requisitos: Windows, Python 3, Echo Dot en **español (US)**, cuenta de Amazon, ngrok.

```powershell
# 1) entorno
cd prueba-alexa\prueba-alexa
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
ngrok config add-authtoken <TOKEN>

# 2) terminal 1: servidor (debe decir 127.0.0.1:5000)
.\venv\Scripts\python.exe app.py

# 3) terminal 2: túnel (copiar la URL https en la consola de Alexa)
ngrok http 5000

# 4) Arduino: subir sensor_diagnostics/sensor_diagnostics.ino y CERRAR el Monitor Serial
```

Prueba en el Echo: *"Alexa, abre hospeda smart"* → *"enciende el ventilador"*.

Señales de éxito: ngrok muestra `POST / 200 OK`; el servidor imprime `[SERIAL] -> VENT_ON` y
`[ARDUINO] OK:VENT_ON`; el ventilador gira.

> Nota: en la consola de Alexa, cada cambio en `interaction_model.json` exige
> **Save → Build Model**, y cada reinicio de ngrok exige actualizar el endpoint.
