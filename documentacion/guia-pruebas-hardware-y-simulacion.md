# Guía de Pruebas: Simulación Local vs. Hardware Real

Esta guía explica en detalle cómo probar el sistema HospedaSmart en dos escenarios:
1. **Hoy (Modo Simulación):** 100% en tu computadora, sin necesidad de tener el Echo Dot ni el Arduino conectados.
2. **Mañana (Hardware Real):** Cuando tengas físicamente el Echo Dot y el kit Keyestudio KS0085.

---

## 🧪 Parte 1: Cómo Probar HOY (Modo Simulación)

En este modo, el sistema se ejecuta en tu laptop usando:
- **FastAPI (`api`)** recibiendo peticiones de voz simuladas.
- **WebSocket** conectando la API con el Gateway.
- **Gateway (`gateway`)** en modo emulador: simula el hardware y confirma las órdenes `OK:<orden>`.
- **Script de prueba (`test_alexa_local.py`)** simulando las frases que dirías a Alexa.

### Paso 1: Preparar los entornos virtuales

Abre una terminal en la raíz del proyecto (`HospedaSmart/`):

```bash
# 1. Configurar dependencias de la API
cd api
python3 -m venv venv
source venv/bin/activate    # En Windows: .\venv\Scripts\activate
pip install -r requirements.txt
deactivate
cd ..

# 2. Configurar dependencias del Gateway
cd gateway
python3 -m venv venv
source venv/bin/activate    # En Windows: .\venv\Scripts\activate
pip install -r requirements.txt
deactivate
cd ..
```

---

### Paso 2: Ejecutar el sistema (3 terminales)

Abre **3 terminales** distintas:

#### Terminal 1 — Iniciar la API
```bash
cd HospedaSmart/api
source venv/bin/activate
python -m api.main
```
> **Qué verás:** 
> `[API] Servidor HospedaSmart iniciado en 0.0.0.0:8000`

---

#### Terminal 2 — Iniciar el Gateway (Simulador)
```bash
cd HospedaSmart/gateway
source venv/bin/activate
# (Si no hay Arduino USB conectado, se activa automáticamente la simulación)
python -m gateway.main
```
> **Qué verás:**
> ```text
> [SERIAL] ⚠️ No se detectó ningún Arduino conectado por USB.
> [SERIAL] 🤖 ACTIVANDO MODO SIMULACIÓN: Las órdenes serán emuladas por software.
> [GATEWAY] ✅ Conexión WebSocket establecida con la API.
> ```

---

#### Terminal 3 — Ejecutar las pruebas de voz
```bash
cd HospedaSmart/api
source venv/bin/activate
python test_alexa_local.py
```
Aparecerá un menú interactivo:
```text
1. Saludo inicial (LaunchRequest)
2. 'Alexa, enciende el ventilador' (EncenderVentiladorIntent)
3. 'Alexa, apaga el ventilador' (ApagarVentiladorIntent)
4. 'Alexa, enciende la luz' (EncenderLuzIntent)
5. 'Alexa, apaga la luz' (ApagarLuzIntent)
6. Ejecutar todas en secuencia
```

Elige la opción **`2`** ("Encender el ventilador") o **`6`** ("Todas").

---

### ¿Qué ocurre internamente en la prueba?

1. **Terminal 3 (Test):** Envía el JSON de `EncenderVentiladorIntent` a `http://localhost:8000/alexa`.
2. **Terminal 1 (API):** Recibe la petición, ejecuta el caso de uso `confort.py`, genera el comando `cmd_xxxx` y lo envía por WebSocket al Gateway.
3. **Terminal 2 (Gateway):** Recibe el comando JSON, lo traduce a `VENT_ON`, el simulador responde `OK:VENT_ON` y envía el `ack` de vuelta.
4. **Terminal 1 (API):** Recibe el `ack` y responde a Alexa: `"Listo, ventilador encendido."`
5. **Terminal 3 (Test):** Imprime: `🗣️ Alexa dice: "Listo, ventilador encendido."`

¡Todo el circuito arquitectónico validado sin hardware!

---

## 🔌 Parte 2: Cómo Probar MAÑANA (Con Hardware Real)

Cuando tengas los dispositivos en mano, la transición es transparente. No hay que cambiar la lógica de negocio ni reescribir código.

### 1. Preparación del Arduino (Kit Keyestudio KS0085)
1. Conecta el Arduino UNO a tu laptop mediante el cable USB.
2. Abre el **Arduino IDE**.
3. Carga el sketch de prueba ubicado en:
   [`prueba-alexa/prueba-alexa/sensor_diagnostics/sensor_diagnostics.ino`](file:///home/phkandres_dell/Documentos/HospedaSmart/prueba-alexa/prueba-alexa/sensor_diagnostics/sensor_diagnostics.ino)
4. Asegúrate de seleccionar la placa **Arduino Uno** y el puerto correcto (ej. `/dev/ttyUSB0` o `COM3`).
5. Pulsa **Subir** (Upload).
6. ⚠️ **MUY IMPORTANTE:** Cierra el Monitor Serial del Arduino IDE. Si lo dejas abierto, el Gateway no podrá acceder al puerto USB.

---

### 2. Configurar la Skill en Amazon Developer Console
1. Ingresa a la [Consola de Desarrolladores de Alexa](https://developer.amazon.com/alexa/console/ask).
2. Abre tu Skill (o crea una Skill Custom llamada `HospedaSmart`, idioma `Spanish (US)`).
3. En la pestaña **Build** -> **Interaction Model** -> **JSON Editor**:
   - Pega el contenido de [`prueba-alexa/prueba-alexa/interaction_model.json`](file:///home/phkandres_dell/Documentos/HospedaSmart/prueba-alexa/prueba-alexa/interaction_model.json).
   - Pulsa **Save Model** y luego **Build Model**.

---

### 3. Exponer tu API local con ngrok
Alexa necesita una URL HTTPS pública para comunicarse con tu laptop:

1. Abre una terminal y corre:
   ```bash
   ngrok http 8000
   ```
2. ngrok te dará una URL como:
   `https://a1b2-c3d4.ngrok-free.app`
3. En la consola de Alexa:
   - Ve a **Endpoint** -> Selecciona **HTTPS**.
   - En **Default Region**, pega tu URL con la ruta `/alexa`:
     `https://a1b2-c3d4.ngrok-free.app/alexa`
   - En el menú desplegable de certificados SSL, selecciona:
     *My development endpoint is a sub-domain of a domain that has a wildcard certificate from a certificate authority*.
   - Pulsa **Save Endpoints**.

---

### 4. Ejecución con Hardware Real

Abre tus terminales:

#### Terminal 1 — API con verificación de firmas activada
Para producción o pruebas con el Echo Dot real, activamos la verificación criptográfica de Amazon:
```bash
cd HospedaSmart/api
source venv/bin/activate
VERIFY_ALEXA_SIGNATURE=true python -m api.main
```

#### Terminal 2 — Gateway (Detectará el Arduino real)
```bash
cd HospedaSmart/gateway
source venv/bin/activate
python -m gateway.main
```
Verás que detecta el puerto:
```text
[SERIAL] Conectando a /dev/ttyUSB0 a 115200 baudios...
[SERIAL] ✅ Conectado exitosamente con hardware real en /dev/ttyUSB0.
[GATEWAY] ✅ Conexión WebSocket establecida con la API.
```

---

### 5. La Prueba de Voz en Vivo

Habla directamente a tu Amazon Echo Dot (debe estar registrado con la misma cuenta de Amazon que la consola de desarrollador):

1. **Invocación:**
   > *"Alexa, abre HospedaSmart"*
   > 🗣️ *"Hola, bienvenido a HospedaSmart. ¿Qué deseas hacer?"*

2. **Orden de Confort:**
   > *"Enciende el ventilador"*
   > 🌀 El ventilador físico del kit comienza a girar.
   > 🗣️ *"Listo, ventilador encendido."*

3. **Orden de Iluminación:**
   > *"Enciende la luz"*
   > 💡 El LED amarillo/blanco del kit se enciende.
   > 🗣️ *"Listo, luz encendida."*

4. **Apagado:**
   > *"Apaga el ventilador"*
   > ⏹️ El ventilador se detiene.
   > 🗣️ *"Listo, ventilador apagado."*

---

## 🛠️ Diagnóstico de Problemas Frecuentes

| Síntoma | Causa común | Solución |
|---|---|---|
| `SerialException: Device or resource busy` | El Monitor Serial del Arduino IDE está abierto. | Cierra el Arduino IDE o su Monitor Serial. |
| Alexa dice: *"Hubo un problema con la respuesta de la skill"* | ngrok cambió de URL o el endpoint no tiene `/alexa`. | Verifica que la URL actual de ngrok esté guardada en la consola de Alexa. |
| El gateway dice: `Timeout esperando ack` | El sketch del Arduino tiene un baudrate distinto. | Verifica que el sketch tenga `Serial.begin(115200)`. |
| Error 400 Bad Request en la API al usar `test_alexa_local.py` | La variable `VERIFY_ALEXA_SIGNATURE` está en `true`. | En pruebas locales sin Echo Dot, usa `VERIFY_ALEXA_SIGNATURE=false`. |
