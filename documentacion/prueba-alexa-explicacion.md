# `prueba-alexa/` explicada — prueba de factibilidad del canal de voz

> **Nota (2026-10-28):** la carpeta `prueba-alexa/` se eliminó del repositorio. Su contenido se
> integró en la arquitectura nueva: los handlers en `api/routers/alexa.py`, la lógica en
> `api/usecases/` (confort y acceso), el puerto serie en `gateway/`, el sketch en
> `firmware/sensor_diagnostics/` y el modelo de interacción y la guía de la consola en `alexa/`.
> Este documento se conserva como registro histórico; el código original sigue en el historial de git.

> Documento de lectura rápida. Explica qué hay dentro de `prueba-alexa/`, cómo funciona y qué
> decisiones de la prueba **no** deberían heredarse a la arquitectura definitiva.
>
> Es una prueba de concepto ("hola mundo"), no un MVP. Su único objetivo fue comprobar que
> la cadena **voz → nube → backend local → hardware** es viable con el kit y el Echo Dot.

---

## 1. Qué demuestra la prueba

Una cadena completa de control por voz, de punta a punta:

```
Persona habla
   │
   ▼
Echo Dot  ──▶  Nube de Alexa (Amazon)
                    │  HTTPS + JSON (petición firmada)
                    ▼
        https://<algo>.ngrok-free.dev     ← túnel público
                    │
                    ▼
   PC (Windows): Flask en 127.0.0.1:5000  ← app.py
                    │  USB serie (pyserial)
                    ▼
   Arduino UNO + Keyestudio KS0085       ← sensor_diagnostics.ino
                    │
                    ▼
        Servo (cerrojo), ventilador, LEDs, buzzer, LCD
```

**Lo que sí quedó probado:** la voz llega al backend, el backend traduce el *intent* en una
orden física, el Arduino la ejecuta y confirma (`OK:<orden>`), y Alexa responde hablando.
Los hitos 1 y 2 están cerrados; el hito 3 (backend → kit por USB) está implementado y en
ajuste fino.

**Lo que no resuelve:** nada de negocio. No hay reservas, ni usuarios, ni base de datos, ni
pagos, ni channel manager, ni panel web, ni multi-habitación.

---

## 2. Estructura de la carpeta

```
prueba-alexa/
├── README-conexion puente alexa.md   ← guía paso a paso de la conexión Alexa ↔ backend
└── prueba-alexa/                     ← carpeta interna (mismo nombre, un nivel más abajo)
    ├── app.py                        ← servidor Flask + handlers de la skill
    ├── interaction_model.json        ← intents y frases que entiende Alexa
    ├── requirements.txt              ← Flask, ask-sdk-core, flask-ask-sdk, pyserial
    ├── README.md                     ← guía técnica corta (instalación/ejecución)
    ├── sensor_diagnostics/
    │   └── sensor_diagnostics.ino    ← sketch Arduino: banco de pruebas + órdenes remotas
    ├── __pycache__/                  ← basura de Python (ignorable)
    └── venv/                         ← entorno virtual de Windows, ~55 MB (ignorable)
```

Notas rápidas:

- Hay **dos README** con información solapada: el de fuera es el narrativo (arquitectura,
  costos, problemas frecuentes); el de dentro es el operativo (comandos).
- La **doble carpeta** `prueba-alexa/prueba-alexa/` es un accidente de creación, no un diseño.
- El `venv/` está creado en **Windows** (`Scripts/`, `Lib/`): no funciona en Linux/macOS.
  Además está sin ignorar en git y pesa 55 MB. No debe versionarse.

---

## 3. Los cuatro archivos que importan

### 3.1 `app.py` — el backend (≈310 líneas)

Servidor **Flask** con el SDK oficial de Alexa (`ask-sdk-core` + `flask-ask-sdk`).
Es el corazón de la prueba.

**a) Conexión con el Arduino (clase `Arduino`)**

- Mantiene el puerto serie abierto y **un lock** (`threading.Lock`), porque Flask atiende
  peticiones en varios hilos y el puerto solo admite un escritor.
- `detectar_puerto()`: busca el único puerto USB conectado; si hay 0 o varios, falla y pide
  definir `SERIAL_PORT` a mano (`"COM3"`).
- Al abrir el puerto el Arduino **se reinicia**; por eso espera 2,5 s (`time.sleep(2.5)`)
  antes de mandar nada.
- `enviar(orden)`: escribe `ORDEN\n`, luego **espera hasta 3 s** a leer `OK:ORDEN`.
  Devuelve `True/False` → de eso depende lo que Alexa contesta.
- Si el cable se desconecta, cierra el puerto y lo reintenta en la siguiente orden.

**b) Handlers (una clase por tipo de petición)**

| Handler | Cuándo se ejecuta | Qué hace |
|---|---|---|
| `LaunchRequestHandler` | "Alexa, abre hospeda smart" | Saluda y deja la sesión abierta (`.ask()`) |
| `OrdenArduinoIntentHandler` | Cualquier intent de control | Envía la orden al Arduino y responde OK o error |
| `HelpIntentHandler` | "ayuda" | Lista las órdenes disponibles |
| `FallbackIntentHandler` | Frase no reconocida | Pide repetir la orden |
| `CancelOrStopIntentHandler` | "cancela" / "para" / "salir" | "Hasta luego" y cierra sesión |
| `SessionEndedRequestHandler` | Alexa cierra la sesión | Solo registra el motivo (no puede hablar) |
| `IntentDesconocidoHandler` | Intent que el servidor no conoce | Avisa que el modelo está desactualizado |
| `LogRequestInterceptor` | **Todas** las peticiones | Imprime tipo de petición e intent elegido |
| `CatchAllExceptionHandler` | Cualquier excepción | Responde en español, nunca deja a Alexa muda |

**c) La tabla `ORDENES`: el "contrato" voz → hardware**

```python
ORDENES = [
    ("EncenderVentiladorIntent", "VENT_ON",        "Listo, ventilador encendido"),
    ("ApagarVentiladorIntent",   "VENT_OFF",       "Listo, ventilador apagado"),
    ("EncenderLuzIntent",        "LUZ_ON",         "Listo, luz encendida"),
    ("ApagarLuzIntent",          "LUZ_OFF",        "Listo, luz apagada"),
    ("AbrirPuertaIntent",        "PUERTA_ABRIR",   "Listo, puerta abierta"),
    ("CerrarPuertaIntent",       "PUERTA_CERRAR",  "Listo, puerta cerrada"),
]
```

Cada fila genera un handler. **Agregar una orden nueva = agregar una fila + una frase en el
modelo de interacción + un `else if` en el sketch.** Tres lugares, ningún acoplamiento
automático: es el punto más frágil del diseño.

**d) Seguridad**

```python
app.config["ASK_SDK_VERIFY_SIGNATURE"] = True   # solo peticiones firmadas por Amazon
app.config["ASK_SDK_VERIFY_TIMESTAMP"] = True   # rechaza peticiones de >150 s
```

Consecuencia: un `curl` o Postman recibe **HTTP 400**. Eso es correcto, no un bug.
`SKILL_ID = None` significa "acepta peticiones de cualquier skill" — cómodo para probar,
peligroso en producción.

### 3.2 `interaction_model.json` — el diccionario de Alexa

Define el nombre de invocación (`hospeda smart`) y, por cada intent, las **frases de
ejemplo** que Alexa usa para clasificar lo que oye:

- `EncenderLuzIntent`: "enciende la luz", "prende el foco", "encienda la luz"…
- `ApagarLuzIntent`, `EncenderVentiladorIntent`, `ApagarVentiladorIntent`,
  `AbrirPuertaIntent` ("abre el cerrojo", "desbloquea la puerta"), `CerrarPuertaIntent`.
- Los `AMAZON.*Intent` (Help, Stop, Cancel, Fallback, NavigateHome) son built-in.

Detalle clave: **este archivo no se lee solo**. Hay que pegarlo a mano en la consola de
Alexa (JSON Editor → Save → Build Model) cada vez que cambie. Por eso el `README` insiste
tanto en el "Build".

El patrón de frases (tú/usted, "el foco"/"la luz") muestra que hubo iteración real: las
formas en subjuntivo ("que **encienda** la luz") se agregaron para que funcionara la frase
única "Alexa, pídele a hospeda smart que encienda la luz".

### 3.3 `sensor_diagnostics.ino` — el firmware (≈925 líneas)

No es un firmware de producción: es un **banco de pruebas de todo el kit**. Tiene tres
funciones mezcladas en un solo archivo:

**a) Mapa de pines (Sensor Shield V5.2)**

| Pin | Componente | Uso en HospedaSmart |
|---|---|---|
| D2 | PIR | Detección de presencia |
| D3 | Buzzer pasivo | Feedback / alarma |
| D4 | Pulsador | Entrada física |
| D5/D6 | L9110 (ventilador) | Extracción / confort (PWM) |
| D7 | Relé 5 V | Corte/energización general |
| D9 | Servo SG90 | Cerrojo de la puerta (0° cerrado, 90° abierto) |
| D12 | LED amarillo | Alerta / servicio |
| D13 | LED blanco | Luz principal de confort |
| A0 | LDR | Luz ambiental |
| A1 | Sensor de vapor/lluvia | Humedad |
| A2 | MQ-2 | Gas / humo |
| A4/A5 | LCD 1602 I2C | Interfaz local (0x27 o 0x3F, autodetecta) |

**b) Menú de diagnóstico por Monitor Serial (115200 baudios)**

- `A` auto-test completo de 6 pasos; `1`–`6` pruebas de servo, ventilador, buzzer, LEDs,
  relé y LCD.
- `7` lectura puntual de sensores; `8` telemetría continua (1 s); `9` modo Serial Plotter
  (CSV a 150 ms); `C` calibración de rango ADC; `B` botón corto/largo; `P` PIR; `I` escáner I2C.
- `S1`/`S2`/`S3`: **simulaciones de escenarios** del proyecto.
  - `S1` control de acceso: PIN `1234` → servo a 90°, chime, 5 s, cierra.
  - `S2` emergencia de gas: ventilador al 100% + sirena + estrobo + LCD, 6 s, normaliza.
  - `S3` confort nocturno: si LDR < 400 enciende luz de cortesía 4 s (ahorro).

**c) Órdenes remotas (las que usa Alexa)**

```cpp
VENT_ON | VENT_OFF | LUZ_ON | LUZ_OFF | PUERTA_ABRIR | PUERTA_CERRAR
```

A diferencia de las pruebas (que terminan y dejan todo apagado), estas **dejan el actuador en
el estado pedido** y responden `OK:<orden>`, que es lo que `app.py` espera leer.

**Problema estructural del sketch:** el `loop()` es bloqueante. Mientras corre una prueba
(`delay`, `while` esperando un PIN, un auto-test completo), el Arduino **no lee el puerto**.
Si Alexa llega en ese momento, no hay confirmación y el backend dice "no pude comunicarme".
Está documentado como limitación, pero es exactamente lo que una arquitectura real no puede
permitirse.

### 3.4 `requirements.txt` — dependencias fijadas

```
Flask==3.1.3
ask-sdk-core==1.19.0
flask-ask-sdk==1.0.0
pyserial==3.5
```

Versiones exactas: bien para reproducibilidad de la demo, pero sin separación
dev/prod ni lockfile real.

---

## 4. Cómo se ejecuta (resumen del README)

Dos terminales en Windows, siempre:

```powershell
# Terminal 1 — backend
.\venv\Scripts\Activate.ps1
python app.py            # escucha en http://127.0.0.1:5000

# Terminal 2 — túnel público
ngrok http 5000          # da una URL https://xxxx.ngrok-free.dev
```

Luego, en la consola de Alexa (`developer.amazon.com/alexa`):

1. Skill *Custom*, locale `es-US`, hosting **"Provision your own"**.
2. Endpoint HTTPS = la URL de ngrok; certificado *"sub-domain with wildcard certificate"*.
3. Pegar `interaction_model.json` en el JSON Editor → **Save** → **Build Model**.
4. Probar en la pestaña *Test* o en el Echo: "Alexa, abre hospeda smart" → "enciende la luz".

Señales de que funciona: `POST / 200` en ngrok, `[SERIAL] -> LUZ_ON` y `[ARDUINO] OK:LUZ_ON`
en la consola de Python.

**Por qué ngrok:** el servidor vive en `127.0.0.1`, la PC está detrás del router sin IP
pública y Alexa exige HTTPS con certificado válido. ngrok resuelve las tres cosas gratis.
Costo total de la prueba: **$0** (cuenta dev de Amazon + skill en modo desarrollo + ngrok free).

---

## 5. Detalles que conviene tener presentes

Cosas que encontré leyendo el código y que no siempre coinciden entre documentos:

1. **Baudrate:** el diagrama del `README-conexion` dice *9600*, pero `app.py`, el `.ino` y el
   `README` interno usan **115200**. El valor real es 115200.
2. **Nombre de invocación:** `interaction_model.json` dice `hospeda smart`; el README de
   conexión habla de `casa smart` en varios ejemplos. El modelo versionado es la fuente de
   verdad.
3. **Modelo del Echo:** el README raíz del proyecto dice Echo Dot 5.ª gen; el README de la
   prueba dice 3.ª gen. Irrelevante técnicamente, pero conviene unificar.
4. **`venv/` versionable:** no hay `.gitignore` en el repo, así que los 55 MB del entorno de
   Windows aparecen como *untracked*. Debe ignorarse antes del primer commit de esta carpeta.
5. **`SKILL_ID = None`:** acepta peticiones de cualquier skill. Poner el ID real es un cambio
   de una línea y elimina un vector de abuso.
6. **La PC es un punto único de fallo:** si se apaga, se cae el servidor o cambia la URL de
   ngrok, la skill deja de responder. Por eso la reacción a gas (`S2`) se resuelve
   **localmente en el Arduino**, sin depender de la nube.

---

## 6. Qué *no* heredar a la arquitectura definitiva

Esta es la parte útil para el siguiente paso. La prueba valida el *camino*, no el *diseño*.
Estos son los atajos conscientes que hay que reemplazar:

| Atajo de la prueba | Por qué no escala | Dirección para la arquitectura |
|---|---|---|
| Un Arduino = una habitación, cable USB a la PC | No hay forma de cubrir N habitaciones | Gateway por habitación (ESP32/RPi) que hable por red (MQTT/HTTP), no USB |
| `app.py` mezcla web, lógica y serie | Un archivo, tres responsabilidades | Separar API/adaptador de voz, dominio y capa de dispositivos |
| Órdenes como strings (`LUZ_ON`) repetidos en 3 archivos | Cambiar una orden obliga a tocar Python, JSON y C++ | Contrato único de comandos (enum/JSON schema) generado o compartido |
| `loop()` bloqueante con `delay()` | El dispositivo queda sordo mientras ejecuta | Máquina de estados no bloqueante (`millis()`), sin `delay` largos |
| ngrok + PC encendida | No es infraestructura, es una laptop | Backend desplegado (VPS/cloud) + endpoint estable; el edge no depende de él |
| Sin persistencia | No hay historial, ni auditoría, ni estado real | Base de datos + estado de dispositivo como fuente de verdad |
| Sin autenticación de usuario | Cualquiera con el Echo controla la puerta | Identidad del huésped, permisos por rol, PIN/OTP, registro de accesos |
| Umbrales hardcodeados (`LDR < 400`, `gas > 450`) | No se calibra por instalación | Configuración por dispositivo + calibración persistida |
| Solo *pull* de Alexa; el kit nunca reporta | El anfitrión no ve telemetría | Telemetría edge → nube (eventos), no solo comandos nube → edge |
| Sin tests, sin logs estructurados, sin config por entorno | Imposible de operar | `.env`, logging JSON, tests del dominio y del contrato |

**La idea central que sí vale la pena conservar:** la **seguridad crítica se resuelve en el
edge**. Gas/humo no puede depender de internet ni de Alexa. La nube aporta coordinación,
historial y control remoto; el dispositivo local garantiza lo que debe pasar en milisegundos.

---

## 7. Preguntas abiertas para cuando planifiquemos la arquitectura

1. ¿El control por voz es un canal **principal** o un **complemento** del panel web/app?
2. ¿Cuántas habitaciones/propiedades simultáneas como objetivo realista del proyecto?
3. ¿Un gateway por habitación o un solo controlador por propiedad con varios nodos?
4. ¿El estado de los dispositivos vive en la nube (fuente de verdad) o en el edge con
   sincronización?
5. ¿Cómo se autentica un huésped para abrir la puerta por voz, si decir el PIN en voz alta
   lo expone (limitación ya detectada en la prueba)?
6. ¿Qué pasa cuando se cae internet? ¿Qué funciones mínimas deben seguir operando?
7. ¿Se mantiene Alexa como VUI o se evalúa una app/PWA como interfaz principal?
8. ¿Stack del backend definitivo? (La prueba usó Flask solo por velocidad; no implica que
   sea la elección final.)

---

## 8. Resumen en cinco líneas

1. `prueba-alexa/` es un **hola mundo end-to-end** del canal de voz: voz → Alexa → ngrok →
   Flask → USB → Arduino.
2. `app.py` recibe *intents*, los mapea a órdenes (`LUZ_ON`…) y espera confirmación del kit.
3. `interaction_model.json` define qué frases entiende Alexa y se carga **a mano** en la consola.
4. `sensor_diagnostics.ino` es un banco de pruebas completo del kit + las órdenes remotas.
5. Funciona y costó $0 — pero es un prototipo de un solo dispositivo, bloqueante y sin
   persistencia: sirve como **referencia de flujo**, no como base de código.
