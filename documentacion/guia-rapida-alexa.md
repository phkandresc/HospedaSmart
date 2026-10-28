# Guía rápida: probar HospedaSmart con Alexa

Pasos mínimos para controlar el kit con la voz. Si algo falla, la guía completa está en
[`alexa/README.md`](../alexa/README.md).

**Qué se puede probar hoy:** luz, ventilador y puerta (la puerta abre **sin PIN** por ahora).

---

## Antes de empezar (una sola vez)

Necesitas: laptop con Windows, Arduino conectado por USB, Echo Dot en **Español (Estados Unidos)**
y una cuenta de Amazon (la misma del Echo).

**1. Instalar el proyecto.** En PowerShell, en la carpeta del repo:
```powershell
py -3.14 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**2. Cargar el sketch al Arduino.** Con Arduino IDE sube
`firmware/sensor_diagnostics/sensor_diagnostics.ino` (placa *Arduino Uno*) y **cierra el
Monitor Serial**.

**3. Configurar ngrok.** Crea una cuenta gratis en [ngrok.com](https://ngrok.com) y ejecuta:
```powershell
ngrok config add-authtoken <TU_TOKEN>
```
En *Domains* del panel de ngrok copia tu dominio gratuito (ej. `algo.ngrok-free.app`). Es fijo,
así no tendrás que cambiar la URL en Alexa cada vez.

**4. Crear la skill** en [developer.amazon.com/alexa](https://developer.amazon.com/alexa/console/ask):
1. **Create Skill** → nombre `HospedaSmart` → idioma **Spanish (US)** → tipo **Custom** →
   hosting **Provision your own** → plantilla *Start from Scratch*.
2. **Build → Interaction Model → JSON Editor** → borra todo, pega el contenido de
   [`alexa/interaction_model.json`](../alexa/interaction_model.json) → **Save** → **Build Model**.
3. **Build → Endpoint** → **HTTPS** → en *Default Region* escribe
   `https://<tu-dominio-ngrok>/alexa` → certificado: *"…sub-domain of a domain that has a wildcard
   certificate…"* → **Save Endpoints**.

---

## Cada vez que quieras probar

Abre **3 ventanas de PowerShell** en la carpeta del repo y en cada una activa el entorno:
`.\venv\Scripts\Activate.ps1`

**Ventana 1 — Comprobar el Arduino (10 segundos):**
```powershell
python -m gateway.test_serial
```
Debe terminar en `6/6 órdenes confirmadas`. Si no, revisa el cable y que el Monitor Serial esté cerrado.

**Ventana 1 — API** (en la misma ventana, cuando termine la prueba anterior):
```powershell
$env:VERIFY_ALEXA_SIGNATURE="true"; $env:VERIFY_ALEXA_TIMESTAMP="true"; python -m api.main
```

**Ventana 2 — Gateway:**
```powershell
$env:SIMULACION="false"; python -m gateway.main
```
Espera a ver `✅ Conectado exitosamente con hardware real` y `✅ Conexión WebSocket establecida`.

**Ventana 3 — Túnel:**
```powershell
ngrok http 8000 --url https://<tu-dominio-ngrok>
```

---

## Qué decirle a Alexa

Primero abre la skill: **"Alexa, abre hospeda smart"** → responde *"Hola, bienvenido a HospedaSmart…"*.
Luego, sin decir "Alexa":

| Dices | Qué pasa en el kit | Alexa responde |
|---|---|---|
| "enciende la luz" | Se enciende el LED blanco | "Listo, luz encendida." |
| "apaga la luz" | Se apaga el LED blanco | "Listo, luz apagada." |
| "enciende el ventilador" | Gira el ventilador | "Listo, ventilador encendido." |
| "apaga el ventilador" | Se detiene | "Listo, ventilador apagado." |
| "abre la puerta" | El servo gira a 90° | "Listo, puerta abierta." |
| "cierra la puerta" | El servo vuelve a 0° | "Listo, puerta cerrada." |
| "ayuda" | — | Te dice qué órdenes existen |
| "salir" | — | "Hasta luego." |

Después de cada orden la skill se cierra. Para la siguiente, vuelve a abrirla o dilo todo en una
frase: **"Alexa, pídele a hospeda smart que encienda el ventilador"**.

> Sin Echo Dot también puedes probar en la consola de Alexa, pestaña **Test** (modo *Development*),
> escribiendo las mismas frases.

---

## Si algo falla

| Síntoma | Solución |
|---|---|
| Alexa: *"Hubo un problema con la respuesta de la skill"* | ¿Corren las 3 ventanas? ¿El endpoint termina en `/alexa`? |
| Alexa: *"No pude comunicarme con la habitación"* | Mira la ventana 2 (gateway): ¿sigue conectado al Arduino? |
| Alexa no reconoce la skill | El Echo debe estar en Español (EE. UU.) y en la misma cuenta de Amazon |
| "Abre la puerta" hace otra cosa | Vuelve a pegar `interaction_model.json` y pulsa **Build Model** |
| El gateway dice `Acceso denegado` en el puerto | Cierra el Monitor Serial de Arduino IDE |
| ngrok muestra `502` | La API (ventana 1) no está corriendo |

**Para terminar:** `Ctrl + C` en cada ventana.
