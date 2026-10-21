# HospedaSmart 🏨💡

**Sistema de automatización global y descentralizado para la gestión integral de hospedajes.**

HospedaSmart es una plataforma innovadora que fusiona la administración logística en la nube con la ejecución física en el sitio. Su propósito es garantizar una experiencia de usuario fluida, segura y eficiente tanto para anfitriones como para huéspedes y personal operativo, automatizando desde el control de acceso hasta la gestión de confort y emergencias.

---

## 🚀 Características Principales

El sistema se divide en cuatro módulos fundamentales que orquestan toda la experiencia operativa y de estancia:

### 1. Gestión de Reservas, Autenticación y Control de Accesos
* **Sincronización en tiempo real:** Integración con Channel Managers (Airbnb, Booking) para evitar sobreventas.
* **Check-in/Check-out Digital:** Procesos desatendidos con validación de identidad (KYC / Biometría).
* **Pagos Integrados:** Cobro dinámico y gestión automática de depósitos de garantía.
* **Control de Acceso Físico:** Desbloqueo de puertas mediante PIN, Bluetooth o validación de voz con Alexa.

### 2. Automatización, Confort y Eficiencia Energética
* **Pre-acondicionamiento climático:** Ajuste térmico automático basado en APIs meteorológicas antes de la llegada del huésped.
* **Iluminación Inteligente:** Sensores de presencia (PIR) y luminosidad (fotorresistencias) para eficiencia energética.
* **Control por Voz:** Gestión del entorno ambiental (luces, ventilación) mediante comandos de voz.

### 3. Gestión de Operaciones, Logística y Mantenimiento
* **Panel de Control en Tiempo Real:** Monitoreo de telemetría y estatus de habitaciones para el anfitrión.
* **Gestión de Tareas por Voz:** El personal de limpieza y mantenimiento puede consultar y actualizar su cronograma interactuando directamente con Alexa.
* **Reporte de Incidencias:** Registro ágil de daños o falta de insumos.

### 4. Seguridad y Protocolos de Emergencia
* **Respuesta Local Automatizada:** Activación de extractores y alarmas ante detección de gases o humo (Sensor MQ-2).
* **Escalamiento al ECU 911:** Integración vía API para notificar emergencias críticas con geolocalización de manera automática.

---

## 🛠️ Arquitectura y Tecnologías

El ecosistema opera en dos niveles de interacción tecnológica:

### Interacciones de Hardware y Voz (Alcance Local - Edge Computing)
* **Kit de Hogar Inteligente Keyestudio KS0085:** Red de microcontroladores equipada con servomotores, módulos Bluetooth, teclados matriciales, pantallas LCD, sensores PIR, fotorresistencias, sensores de gas (MQ-2) y humedad.
* **Asistente de Voz:** Amazon Echo Dot (5ta Generación) que funciona como Interfaz de Usuario Conversacional (VUI) mediante Alexa Voice Service.

### Interacciones de Software (Alcance Global / Nube)
Integración mediante APIs / Webhooks con los siguientes servicios de terceros:
* **Gestor de Canales (Channel Manager)**
* **Sistemas de Validación de Identidad (KYC/Biometría)**
* **Pasarelas de Pagos**
* **Servicios Meteorológicos**
* **Sistema Integrado de Emergencias (ECU 911)**

---

## 👥 Roles de Usuario

1. **Anfitrión:** Administra remotamente las propiedades, reservas, personal y supervisa alertas críticas a través de un panel unificado.
2. **Huésped:** Disfruta de una estancia autónoma con check-in digital, acceso sin llaves y control de su entorno mediante comandos de voz.
3. **Personal de Limpieza:** Consulta y reporta la finalización de sus labores de aseo utilizando comandos de voz en las habitaciones.
4. **Personal de Mantenimiento:** Recibe alertas de hardware, da seguimiento a órdenes de trabajo y calibra los dispositivos IoT del recinto.

---
