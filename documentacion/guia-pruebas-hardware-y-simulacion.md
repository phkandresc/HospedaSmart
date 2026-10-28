# Guía de Pruebas: Simulación, Arduino y Alexa

Esta guía explica cómo probar HospedaSmart por etapas, de menos a más piezas:

| Nivel | Qué se prueba | Necesita |
|---|---|---|
| **0. Simulación** | API ↔ Gateway, sin hardware | Solo la laptop |
| **1. PC ↔ Arduino** | El sketch responde a las órdenes por USB | Arduino |
| **2. PC → API → Gateway → Arduino** | La arquitectura completa, sin voz | Arduino |
| **3. Alexa** | La voz real llega hasta el Arduino | Arduino + Echo Dot + ngrok |

Si un nivel falla, no sigas al siguiente: el problema está en la pieza que acabas de añadir.

> Todos los comandos se ejecutan **desde la raíz del repositorio** (`hospedasmart/`), no desde
> dentro de `api/` o `gateway/`: los módulos se llaman `api.main` y `gateway.main`.

---

## ⚙️ Preparación (una sola vez)

Usa **Python 3.11 a 3.14**. Con Python 3.15 algunas dependencias (p. ej. `pyyaml`) aún no tienen
binarios para Windows y la instalación falla pidiendo Visual Studio. Con el lanzador `py`:

```powershell
py -0p                       # lista las versiones instaladas
py -3.14 -m venv venv        # un solo entorno para API y gateway, en la raíz
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

En Linux/macOS: `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`.

### Cargar el sketch en el Arduino

1. Conecta el Arduino (Keyestudio KS0085) por USB.
2. Abre en Arduino IDE [`prueba-alexa/prueba-alexa/sensor_diagnostics/sensor_diagnostics.ino`](../prueba-alexa/prueba-alexa/sensor_diagnostics/sensor_diagnostics.ino).
   Necesita las librerías **LiquidCrystal I2C** y **Servo**.
3. Placa **Arduino Uno**, puerto correcto (`COM3`, `/dev/ttyUSB0`…) → **Subir**.
4. ⚠️ **Cierra el Monitor Serial.** Si queda abierto, el puerto está ocupado y la PC no puede usarlo.

Para saber qué puerto es: en Arduino IDE (*Herramientas → Puerto*) o en PowerShell
`Get-CimInstance Win32_SerialPort | Select DeviceID,Description`. Los puertos
"Serie estándar sobre el vínculo Bluetooth" **no** son el Arduino.

### Variables de entorno útiles

| Variable | Valores | Para qué |
|---|---|---|
| `SERIAL_PORT` | `COM3`, `/dev/ttyUSB0` | Fija el puerto. Si no se define, se detecta solo. |
| `SIMULACION` | sin definir / `true` / `false` | Automático / siempre simular / **exigir Arduino real** |
| `BAUDRATE` | `115200` | Debe coincidir con `Serial.begin(...)` del sketch |
| `VERIFY_ALEXA_SIGNATURE` | `false` / `true` | `true` solo con el Echo real (nivel 3) |

En PowerShell se definen así: `$env:SIMULACION="false"` (duran lo que dure esa terminal).

> **Durante las pruebas con hardware usa `SIMULACION=false`.** En modo automático, si el puerto
> está ocupado el gateway pasa al simulador y todo "funciona" sin tocar el Arduino. Con `false`
> se detiene y te dice por qué.

---

## 🧪 Nivel 0 — Simulación (sin hardware)

Dos terminales, ambas con el venv activado:

```powershell
# Terminal 1 — API
python -m api.main

# Terminal 2 — Gateway en modo simulación
$env:SIMULACION="true"; python -m gateway.main
```

Verás `[SERIAL] 🤖 ACTIVANDO MODO SIMULACIÓN` y `[GATEWAY] ✅ Conexión WebSocket establecida`.
Prueba con el nivel 2 (`python -m api.test_hardware_local`) o con el simulador de Alexa
(`python api\test_alexa_local.py 6`).

---

## 🔌 Nivel 1 — PC ↔ Arduino (sin API ni Alexa)

Comprueba solo el cable, el puerto y el sketch. **No arranques el gateway** (ocuparía el puerto).

```powershell
python -m gateway.test_serial              # secuencia automática
python -m gateway.test_serial -p COM3      # con puerto explícito
python -m gateway.test_serial -i           # interactivo: escribes VENT_ON, LUZ_OFF...
```

Envía `LUZ_ON/OFF`, `VENT_ON/OFF`, `PUERTA_ABRIR/CERRAR` y espera `OK:<orden>` de cada una:

```text
✅ LUZ_ON             79 ms   ¿Se encendió el LED blanco (D13)?
✅ VENT_ON            80 ms   ¿Gira el ventilador?
✅ PUERTA_ABRIR       91 ms   ¿El servo (D9) giró a 90°?
...
Resultado: 6/6 órdenes confirmadas por el Arduino.
```

El ✅ significa que el Arduino **confirmó** la orden; mira también el kit para comprobar que el
actuador se movió (un ✅ con el ventilador quieto apunta a cableado o alimentación).

Al abrir el puerto el Arduino se reinicia; la herramienta espera a que termine de arrancar (unos
3 s con este sketch) antes de enviar la primera orden.

---

## 🏗️ Nivel 2 — PC → API → Gateway → Arduino (arquitectura completa, sin voz)

```powershell
# Terminal 1 — API
python -m api.main

# Terminal 2 — Gateway exigiendo hardware real
$env:SIMULACION="false"; python -m gateway.main

# Terminal 3 — Prueba
python -m api.test_hardware_local
```

```text
✅ API y gateway conectados.
✅ encender luz              82 ms  → Listo, luz encendida.
✅ encender ventilador       84 ms  → Listo, ventilador encendido.
...
Resultado: 4/4 órdenes confirmadas.
```

También puedes mandar órdenes a mano desde el navegador en **http://localhost:8000/docs**
(sección *dispositivos*), o con PowerShell:

```powershell
Invoke-RestMethod http://localhost:8000/dispositivos/estado
Invoke-RestMethod -Method Post http://localhost:8000/dispositivos/ventilador/encender
```

`POST /dispositivos/{ventilador|luz}/{encender|apagar}` usa **el mismo caso de uso** (`confort.py`)
que Alexa, así que si esto funciona, lo único que queda por probar en el nivel 3 es la voz.

### ¿Qué ocurre internamente?

1. `POST /dispositivos/luz/encender` → `controlar_confort("luz", "encender")`.
2. La API genera `cmd_xxxx` y lo envía por WebSocket al gateway; espera el `ack` hasta 2,5 s.
3. El gateway traduce a `LUZ_ON`, lo escribe por USB y espera `OK:LUZ_ON` hasta 2 s.
4. El gateway responde el `ack` y la API devuelve `"Listo, luz encendida."`.

La espera del gateway (2 s) es menor que la de la API (2,5 s) a propósito: así un fallo del
Arduino llega a la API como "no confirmado" antes de que la API se rinda.

---

## 🗣️ Nivel 3 — Con Alexa (Echo Dot real)

Solo cuando el nivel 2 pase.

1. **Skill** en la [consola de Alexa](https://developer.amazon.com/alexa/console/ask), con la misma
   cuenta del Echo: *Custom*, idioma *Spanish (US)*, hosting propio.
2. **Build → Interaction Model → JSON Editor:** pega
   [`prueba-alexa/prueba-alexa/interaction_model.json`](../prueba-alexa/prueba-alexa/interaction_model.json)
   → **Save** → **Build**. La invocación es **"hospeda smart"**.
3. **Túnel:** `ngrok http 8000` y copia la URL `https://…`.
4. **Build → Endpoint → HTTPS:** `https://<tu-url-ngrok>/alexa` (**con `/alexa`**), certificado
   *"…sub-domain of a domain that has a wildcard certificate…"* → **Save Endpoints**.
5. Arranca la API con verificación de firma y el gateway como en el nivel 2:
   ```powershell
   $env:VERIFY_ALEXA_SIGNATURE="true"; $env:VERIFY_ALEXA_TIMESTAMP="true"; python -m api.main
   ```
6. Di: *"Alexa, abre hospeda smart"* → *"enciende el ventilador"*.

Con la firma activada, `test_alexa_local.py` recibe error 400 (sus peticiones no están firmadas
por Amazon); para usarlo arranca la API sin esas variables.

---

## 🛠️ Diagnóstico de problemas frecuentes

| Síntoma | Causa común | Solución |
|---|---|---|
| `PermissionError(13, 'Acceso denegado')` / `Device or resource busy` | El Monitor Serial u otro programa (otro gateway, `test_serial`) tiene el puerto | Cierra el Monitor Serial y los demás procesos que lo usen |
| El Arduino no responde nada (ni texto) | El sketch cargado no es `sensor_diagnostics.ino` o tiene otro baudrate | Vuelve a subir el sketch; debe tener `Serial.begin(115200)` |
| `Timeout: No se recibió 'OK:...'` solo en la primera orden | La orden llegó mientras el Arduino arrancaba | Ya se corrige solo; si persiste, el sketch tarda más de 6 s en arrancar |
| ✅ en pantalla pero el actuador no se mueve | Cableado o alimentación del kit | Revisa el mapa de pines en `firmware/README.md` |
| Gateway en "MODO SIMULACIÓN" con el Arduino conectado | Puerto ocupado o no detectado (modo automático) | Usa `SIMULACION=false` y `SERIAL_PORT=COMx` |
| `test_hardware_local` dice que el gateway no está conectado | El gateway no arrancó o se cayó | Revisa la terminal del gateway |
| `pip install` falla con "Unable to find a compatible Visual Studio" | Python 3.15 | Crea el venv con `py -3.14` |
| `ModuleNotFoundError: No module named 'api'` | Ejecutaste desde dentro de `api/` | Ejecuta desde la raíz del repo |
| Alexa: *"Hubo un problema con la respuesta de la skill"* | ngrok cambió de URL o al endpoint le falta `/alexa` | Actualiza el endpoint en la consola |
