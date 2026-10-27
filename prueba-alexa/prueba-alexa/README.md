# HospedaSmart: endpoint propio para Alexa (prueba de factibilidad)

Servidor Flask en Windows que recibe las peticiones de una custom skill de Alexa (es-US)
expuesta a Internet con ngrok.

```
Alexa  ->  https://xxxx.ngrok-free.app  ->  ngrok  ->  http://localhost:5000/  ->  app.py  ->  USB  ->  Arduino
```

## Archivos

| Archivo                   | Qué hace |
|---------------------------|----------|
| `app.py`                  | Servidor Flask con los handlers de la skill. Cada intent de control envía una orden al Arduino por USB con `pyserial`. |
| `sensor_diagnostics.ino`  | Sketch del Arduino: menú de pruebas + órdenes remotas (`VENT_ON`, `VENT_OFF`, `LUZ_ON`, `LUZ_OFF`, `PUERTA_ABRIR`, `PUERTA_CERRAR`) que responden `OK:<orden>`. |
| `interaction_model.json`  | Modelo de interacción para pegar en el *JSON Editor* de la consola de Alexa. |
| `requirements.txt` | Dependencias con versiones fijas: Flask, ask-sdk-core, flask-ask-sdk y pyserial. |
| `venv/`            | Entorno virtual con las dependencias instaladas (no se sube al repositorio). |

## Instalación (solo la primera vez)

```powershell
cd C:\Users\eduar\Desktop\HospedaSmart\prueba-alexa
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Ejecución

Terminal 1, el servidor:

```powershell
cd C:\Users\eduar\Desktop\HospedaSmart\prueba-alexa
.\venv\Scripts\Activate.ps1
python app.py
```

> Si PowerShell bloquea `Activate.ps1`, usa directamente `.\venv\Scripts\python.exe app.py`.

Terminal 2, el túnel HTTPS:

```powershell
ngrok http 5000
```

## Configuración en la consola de Alexa (developer.amazon.com)

1. **Endpoint**: elige *HTTPS* y pega la URL `https://xxxx.ngrok-free.app/` que muestra ngrok.
2. **Certificado SSL**: elige *"My development endpoint is a sub-domain of a domain that has a wildcard certificate from a certificate authority"*.
3. **Interaction Model**: en *Interaction Model > JSON Editor* pega el contenido de
   `interaction_model.json`. Luego haz *Save* y *Build Model*.
4. (Opcional) Copia el Skill ID en `SKILL_ID` dentro de `app.py` para aceptar solo tu skill.
5. Prueba en la pestaña *Test*: "pídele a hospeda smart que encienda el ventilador".
   En la consola del servidor deben aparecer `[SERIAL] -> VENT_ON` y `[ARDUINO] OK:VENT_ON`.

> La URL gratuita de ngrok cambia cada vez que lo reinicias. Si cambia, actualiza el endpoint en la consola de Alexa.

## Seguridad

La verificación de firma y de timestamp de Alexa está activa (`ASK_SDK_VERIFY_SIGNATURE` y
`ASK_SDK_VERIFY_TIMESTAMP` en `True`). Por eso una petición hecha a mano (por ejemplo con
Postman o curl) recibe **HTTP 400**: es lo esperado. Solo Alexa puede invocar el servidor.

## Arduino

1. Sube `sensor_diagnostics.ino` con el Arduino IDE (115200 baudios).
2. **Cierra el Monitor Serial del IDE**: solo un programa puede usar el puerto COM a la vez.
3. `app.py` detecta solo el puerto USB. Si no lo encuentra o hay varios, escribe el puerto
   (por ejemplo `"COM3"`) en `SERIAL_PORT`. Para ver los puertos:
   `.\venv\Scripts\python.exe -m serial.tools.list_ports -v`
4. Al abrir el puerto el Arduino se reinicia; el servidor espera 2.5 s antes de enviar órdenes.
   Si el Arduino está ocupado en una prueba del menú (por ejemplo `S1` esperando el PIN),
   no confirmará la orden y Alexa dirá que no pudo comunicarse.
