/*
 * =====================================================================================
 * HospedaSmart - Banco de Pruebas y Diagnóstico Integral Exhaustivo
 * Kit: Keyestudio Smart Home Kit KS0085 (Arduino Uno / Keyestudio Plus)
 * =====================================================================================
 * Este programa permite probar al 100% todos los sensores y actuadores del kit
 * tanto de forma automática como interactiva a través del Monitor Serial (115200 baudios).
 *
 * Mapeo de Pines (Sensor Shield V5.2):
 *  - D2 : Sensor de Movimiento PIR
 *  - D3 : Zumbador / Buzzer Pasivo
 *  - D4 : Pulsador / Botón Físico
 *  - D5 : Motor Ventilador L9110 (INA - PWM)
 *  - D6 : Motor Ventilador L9110 (INB - PWM)
 *  - D7 : Módulo Relé 5V
 *  - D9 : Servomotor SG90 (Cerrojo)
 *  - D12: LED Amarillo (Alerta / Limpieza)
 *  - D13: LED Blanco (Confort / Luz Principal)
 *  - A0 : Fotorresistencia LDR (Luz Ambiente)
 *  - A1 : Sensor de Vapor / Gotas de Lluvia
 *  - A2 : Sensor de Gas MQ-2
 *  - A4/A5: Pantalla LCD 1602 I2C (SDA / SCL)
 * =====================================================================================
 */

#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Servo.h>

// Definición de Pines de Hardware
const int PIN_PIR        = 2;
const int PIN_BUZZER     = 3;
const int PIN_BUTTON     = 4;
const int PIN_FAN_INA    = 5;
const int PIN_FAN_INB    = 6;
const int PIN_RELAY      = 7;
const int PIN_SERVO      = 9;
const int PIN_LED_YELLOW = 12;
const int PIN_LED_WHITE  = 13;

const int PIN_LDR        = A0;
const int PIN_STEAM      = A1;
const int PIN_GAS_MQ2    = A2;

// Objetos de Control
Servo doorServo;
LiquidCrystal_I2C lcd27(0x27, 16, 2);
LiquidCrystal_I2C lcd3F(0x3F, 16, 2);
LiquidCrystal_I2C* activeLcd = nullptr;
bool lcdDetected = false;

// Variables de Estado de Telemetría
bool telemetryLive = false;
bool plotterLive   = false;
unsigned long lastStreamTime = 0;

// =====================================================================================
// UTILIDADES DE PANTALLA LCD (Tolerante a desconexión)
// =====================================================================================
bool initLcdIfPresent() {
  Wire.begin();
  // Verificar dirección 0x27
  Wire.beginTransmission(0x27);
  if (Wire.endTransmission() == 0) {
    activeLcd = &lcd27;
    activeLcd->init();
    activeLcd->backlight();
    lcdDetected = true;
    return true;
  }
  // Verificar dirección 0x3F
  Wire.beginTransmission(0x3F);
  if (Wire.endTransmission() == 0) {
    activeLcd = &lcd3F;
    activeLcd->init();
    activeLcd->backlight();
    lcdDetected = true;
    return true;
  }
  activeLcd = nullptr;
  lcdDetected = false;
  return false;
}

void lcdShow(const __FlashStringHelper* line1, const __FlashStringHelper* line2) {
  if (!activeLcd) return;
  activeLcd->clear();
  activeLcd->setCursor(0, 0);
  activeLcd->print(line1);
  activeLcd->setCursor(0, 1);
  activeLcd->print(line2);
}

// =====================================================================================
// MENÚ PRINCIPAL
// =====================================================================================
void printMainMenu() {
  Serial.println(F("\n=================================================================="));
  Serial.println(F("      HOSPEDASMART - BANCO DE PRUEBAS INTEGRAL EXHAUSTIVO         "));
  Serial.println(F("              Keyestudio Smart Home Kit KS0085                    "));
  Serial.println(F("=================================================================="));
  Serial.println(F(" [A] AUTO-TEST COMPLETO (Secuencia de diagnóstico de fábrica)    "));
  Serial.println(F("------------------------------------------------------------------"));
  Serial.println(F(" ACTUADORES:"));
  Serial.println(F("  [1] Servomotor SG90 (Test de posiciones 0, 45, 90, 180 deg)    "));
  Serial.println(F("  [2] Motor Ventilador L9110 (Giro directo, inverso y rampa PWM)  "));
  Serial.println(F("  [3] Zumbador / Buzzer (Melodía, tono de alarma y escala sonora) "));
  Serial.println(F("  [4] LEDs Blanco y Amarillo (Individual, estroboscópico, noche)  "));
  Serial.println(F("  [5] Módulo Relé 5V (Conmutación simple y prueba de 3 ciclos)    "));
  Serial.println(F("  [6] Pantalla LCD 1602 I2C (Texto, backlight y desplazamiento)   "));
  Serial.println(F("------------------------------------------------------------------"));
  Serial.println(F(" SENSORES Y TELEMETRÍA:"));
  Serial.println(F("  [7] Lectura puntual de todos los sensores                       "));
  Serial.println(F("  [8] Telemetría continua en vivo (Formato texto cada 1s)         "));
  Serial.println(F("  [9] Modo Serial Plotter (Curvas CSV en tiempo real Ctrl+Shift+L)"));
  Serial.println(F("  [C] Calibración y rango dinámico ADC (LDR, MQ-2, Lluvia - 10s)  "));
  Serial.println(F("  [B] Test interactivo de Botón D4 (Detección corta vs larga)     "));
  Serial.println(F("  [P] Test de Sensor de Movimiento PIR D2 (Presencia y duración)  "));
  Serial.println(F("  [I] Escaneo de Direcciones I2C (A4/A5)                          "));
  Serial.println(F("------------------------------------------------------------------"));
  Serial.println(F(" SIMULACIÓN DE ESCENARIOS HOSPEDASMART:"));
  Serial.println(F("  [S1] Escenario 1: Control de Acceso (Validación PIN y cerrojo)  "));
  Serial.println(F("  [S2] Escenario 2: Emergencia de Gas MQ-2 (Extractor + Alarma)   "));
  Serial.println(F("  [S3] Escenario 3: Confort Nocturno (Luz auto con LDR + PIR)     "));
  Serial.println(F("------------------------------------------------------------------"));
  Serial.println(F(" CONTROL REMOTO (Alexa / servidor Python):"));
  Serial.println(F("  VENT_ON | VENT_OFF | LUZ_ON | LUZ_OFF | PUERTA_ABRIR | PUERTA_CERRAR"));
  Serial.println(F("------------------------------------------------------------------"));
  Serial.println(F("  [M] Volver a mostrar este menú                                  "));
  Serial.println(F("=================================================================="));
  Serial.print(F("Seleccione una opción: "));
}

// =====================================================================================
// SETUP & LOOP
// =====================================================================================
void setup() {
  Serial.begin(115200);
  while (!Serial) { ; }

  // Configuración de Pines
  pinMode(PIN_PIR, INPUT);
  pinMode(PIN_BUTTON, INPUT_PULLUP);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_FAN_INA, OUTPUT);
  pinMode(PIN_FAN_INB, OUTPUT);
  pinMode(PIN_RELAY, OUTPUT);
  pinMode(PIN_LED_YELLOW, OUTPUT);
  pinMode(PIN_LED_WHITE, OUTPUT);

  // Estados iniciales seguros
  digitalWrite(PIN_BUZZER, LOW);
  digitalWrite(PIN_FAN_INA, LOW);
  digitalWrite(PIN_FAN_INB, LOW);
  digitalWrite(PIN_RELAY, LOW);
  digitalWrite(PIN_LED_YELLOW, LOW);
  digitalWrite(PIN_LED_WHITE, LOW);

  // Inicializar Servomotor
  doorServo.attach(PIN_SERVO);
  doorServo.write(0);

  // Inicializar Pantalla LCD si está conectada
  bool lcdOk = initLcdIfPresent();

  Serial.println(F("\n=================================================================="));
  Serial.println(F(" [INICIO] Sistema de diagnóstico HospedaSmart cargado con éxito. "));
  if (lcdOk) {
    Serial.println(F(" [HARDWARE] Pantalla LCD 1602 I2C DETECTADA y lista."));
    lcdShow(F(" HospedaSmart   "), F(" Diagnostic OK  "));
  } else {
    Serial.println(F(" [AVISO] Pantalla LCD no detectada en 0x27 ni 0x3F (Continuando en Serial)."));
  }
  Serial.println(F("=================================================================="));

  printMainMenu();
}

void loop() {
  // 1. Atender comandos del Monitor Serial
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    if (input.length() == 0) return;

    input.toUpperCase();
    char cmd = input.charAt(0);

    // Apagar streams continuos si el usuario ingresa un comando
    if (telemetryLive || plotterLive) {
      telemetryLive = false;
      plotterLive = false;
      Serial.println(F("\n[INFO] Transmisión en vivo DETENIDA."));
    }

    if (ejecutarOrdenRemota(input)) {
      // Orden enviada por el servidor Python (Alexa); ya respondió "OK:<orden>".
    } else if (input == "S1") {
      simularControlAcceso();
    } else if (input == "S2") {
      simularEmergenciaGas();
    } else if (input == "S3") {
      simularConfortLuz();
    } else {
      switch (cmd) {
        case 'A': ejecutarAutoTestCompleto(); break;
        case '1': probarServomotorCompleto(); break;
        case '2': probarVentiladorL9110(); break;
        case '3': probarBuzzerSonidos(); break;
        case '4': probarLedsCompleto(); break;
        case '5': probarReleCompleto(); break;
        case '6': probarLCDCompleto(); break;
        case '7': leerSensoresPuntual(); break;
        case '8':
          telemetryLive = true;
          Serial.println(F("\n[TELEMETRÍA] Iniciando transmisión continua cada 1s."));
          Serial.println(F("Presione cualquier tecla y ENTER para detener..."));
          break;
        case '9':
          plotterLive = true;
          Serial.println(F("\n[PLOTTER] Formato: LDR,Gas,Lluvia,PIR,Boton"));
          Serial.println(F("Abre 'Herramientas > Serial Plotter' (Ctrl+Shift+L)"));
          Serial.println(F("Presione cualquier tecla y ENTER para detener..."));
          break;
        case 'C': calibrarSensoresADC(); break;
        case 'B': probarBotonInteractivo(); break;
        case 'P': probarSensorPIR(); break;
        case 'I': escanearI2CExhaustivo(); break;
        case 'M': printMainMenu(); break;
        default:
          Serial.println(F("[ERROR] Comando no reconocido. Ingrese 'M' para ver el menú."));
          break;
      }
    }
  }

  // 2. Transmisión periódica en vivo
  unsigned long now = millis();
  if (telemetryLive && (now - lastStreamTime >= 1000)) {
    lastStreamTime = now;
    leerSensoresPuntual();
  }

  if (plotterLive && (now - lastStreamTime >= 150)) {
    lastStreamTime = now;
    enviarDatosPlotter();
  }
}

// =====================================================================================
// CONTROL REMOTO (Servidor Python / Alexa)
// =====================================================================================
// A diferencia de las pruebas, estas órdenes dejan el actuador en el estado pedido
// y responden "OK:<orden>" para que el servidor confirme que se ejecutaron.

bool ejecutarOrdenRemota(const String& orden) {
  if (orden == "VENT_ON") {
    digitalWrite(PIN_FAN_INA, HIGH);
    digitalWrite(PIN_FAN_INB, LOW);
    lcdShow(F("ORDEN ALEXA     "), F("Ventilador ON   "));
  } else if (orden == "VENT_OFF") {
    digitalWrite(PIN_FAN_INA, LOW);
    digitalWrite(PIN_FAN_INB, LOW);
    lcdShow(F("ORDEN ALEXA     "), F("Ventilador OFF  "));
  } else if (orden == "LUZ_ON") {
    digitalWrite(PIN_LED_WHITE, HIGH);
    lcdShow(F("ORDEN ALEXA     "), F("Luz ON          "));
  } else if (orden == "LUZ_OFF") {
    digitalWrite(PIN_LED_WHITE, LOW);
    lcdShow(F("ORDEN ALEXA     "), F("Luz OFF         "));
  } else if (orden == "PUERTA_ABRIR") {
    doorServo.write(90);
    lcdShow(F("ORDEN ALEXA     "), F("Puerta abierta  "));
  } else if (orden == "PUERTA_CERRAR") {
    doorServo.write(0);
    lcdShow(F("ORDEN ALEXA     "), F("Puerta cerrada  "));
  } else {
    return false;
  }
  Serial.print(F("OK:"));
  Serial.println(orden);
  return true;
}

// =====================================================================================
// PRUEBAS DE ACTUADORES
// =====================================================================================

void probarServomotorCompleto() {
  Serial.println(F("\n--- [PRUEBA 1: SERVOMOTOR SG90 (CERROJO)] ---"));
  lcdShow(F("TEST SERVOMOTOR "), F("Iniciando...    "));

  const int angles[] = {0, 45, 90, 135, 180, 0};
  const char* labels[] = {"0 deg (Cerrado)", "45 deg (Parcial)", "90 deg (Abierto HospedaSmart)", "135 deg (Extra)", "180 deg (Maximo)", "0 deg (Reposo)"};

  for (int i = 0; i < 6; i++) {
    Serial.print(F(" -> Posicionando a: "));
    Serial.println(labels[i]);
    doorServo.write(angles[i]);
    delay(1200);
  }

  Serial.println(F(" -> Realizando barrido suave de 0 a 90 grados..."));
  for (int pos = 0; pos <= 90; pos += 2) {
    doorServo.write(pos);
    delay(20);
  }
  delay(500);

  Serial.println(F(" -> Regresando suavemente de 90 a 0 grados..."));
  for (int pos = 90; pos >= 0; pos -= 2) {
    doorServo.write(pos);
    delay(20);
  }

  Serial.println(F("[OK] Prueba de servomotor completada exitosamente."));
  lcdShow(F("TEST SERVOMOTOR "), F("Finalizado OK   "));
}

void probarVentiladorL9110() {
  Serial.println(F("\n--- [PRUEBA 2: MOTOR VENTILADOR L9110 (D5/D6)] ---"));
  lcdShow(F("TEST VENTILADOR "), F("Giro Directo... "));

  Serial.println(F(" 1. Giro DIRECTO (Extracción de aire al 100% durante 2.5s)..."));
  digitalWrite(PIN_FAN_INA, HIGH);
  digitalWrite(PIN_FAN_INB, LOW);
  delay(2500);

  Serial.println(F(" 2. Frenado / Pausa activa (0.8s)..."));
  digitalWrite(PIN_FAN_INA, LOW);
  digitalWrite(PIN_FAN_INB, LOW);
  delay(800);

  Serial.println(F(" 3. Giro INVERSO (Inyección de aire al 100% durante 2.5s)..."));
  lcdShow(F("TEST VENTILADOR "), F("Giro Inverso... "));
  digitalWrite(PIN_FAN_INA, LOW);
  digitalWrite(PIN_FAN_INB, HIGH);
  delay(2500);

  Serial.println(F(" 4. Frenado / Pausa activa (0.8s)..."));
  digitalWrite(PIN_FAN_INA, LOW);
  digitalWrite(PIN_FAN_INB, LOW);
  delay(800);

  Serial.println(F(" 5. Rampa de Velocidad PWM (30% -> 60% -> 100%)..."));
  lcdShow(F("TEST VENTILADOR "), F("Rampa PWM Speed "));
  
  Serial.println(F("    - 30% PWM..."));
  analogWrite(PIN_FAN_INA, 80);
  delay(1200);

  Serial.println(F("    - 60% PWM..."));
  analogWrite(PIN_FAN_INA, 160);
  delay(1200);

  Serial.println(F("    - 100% PWM..."));
  analogWrite(PIN_FAN_INA, 255);
  delay(1500);

  digitalWrite(PIN_FAN_INA, LOW);
  digitalWrite(PIN_FAN_INB, LOW);
  Serial.println(F("[OK] Motor detenido. Prueba de ventilador finalizada."));
  lcdShow(F("TEST VENTILADOR "), F("Finalizado OK   "));
}

void probarBuzzerSonidos() {
  Serial.println(F("\n--- [PRUEBA 3: ZUMBADOR / BUZZER PASIVO (D3)] ---"));
  lcdShow(F("TEST BUZZER D3  "), F("Tonos de prueba "));

  Serial.println(F(" 1. Melodía de Acceso Concedido (Chime agudo)..."));
  tone(PIN_BUZZER, 1760, 100); delay(120);
  tone(PIN_BUZZER, 2093, 120); delay(140);
  tone(PIN_BUZZER, 2637, 200); delay(300);
  noTone(PIN_BUZZER);

  delay(600);
  Serial.println(F(" 2. Tono de Rechazo / Acceso Denegado (Grave)..."));
  tone(PIN_BUZZER, 350, 400); delay(500);
  noTone(PIN_BUZZER);

  delay(600);
  Serial.println(F(" 3. Sirena de Alerta de Fuga de Gas (Peligro)..."));
  for (int i = 0; i < 4; i++) {
    tone(PIN_BUZZER, 1800, 120); delay(130);
    tone(PIN_BUZZER, 2400, 120); delay(130);
  }
  noTone(PIN_BUZZER);

  delay(600);
  Serial.println(F(" 4. Escala Musical Diatónica (Do, Re, Mi, Fa, Sol, La, Si, Do)..."));
  const int scale[] = {262, 294, 330, 349, 392, 440, 494, 523};
  for (int i = 0; i < 8; i++) {
    tone(PIN_BUZZER, scale[i], 120);
    delay(150);
  }
  noTone(PIN_BUZZER);

  Serial.println(F("[OK] Prueba de zumbador finalizada."));
  lcdShow(F("TEST BUZZER D3  "), F("Finalizado OK   "));
}

void probarLedsCompleto() {
  Serial.println(F("\n--- [PRUEBA 4: LEDS BLANCO (D13) Y AMARILLO (D12)] ---"));
  lcdShow(F("TEST LEDS       "), F("Verificando...  "));

  Serial.println(F(" 1. Encendiendo LED Blanco D13 (Luz principal de confort) por 1.5s..."));
  digitalWrite(PIN_LED_WHITE, HIGH);
  delay(1500);
  digitalWrite(PIN_LED_WHITE, LOW);

  Serial.println(F(" 2. Encendiendo LED Amarillo D12 (Luz de servicio/alerta) por 1.5s..."));
  digitalWrite(PIN_LED_YELLOW, HIGH);
  delay(1500);
  digitalWrite(PIN_LED_YELLOW, LOW);

  Serial.println(F(" 3. Efecto Estroboscópico de Emergencia (Alerta visual rápida)..."));
  for (int i = 0; i < 6; i++) {
    digitalWrite(PIN_LED_WHITE, HIGH);
    digitalWrite(PIN_LED_YELLOW, LOW);
    delay(80);
    digitalWrite(PIN_LED_WHITE, LOW);
    digitalWrite(PIN_LED_YELLOW, HIGH);
    delay(80);
  }
  digitalWrite(PIN_LED_YELLOW, LOW);

  Serial.println(F(" 4. Simulación de Luz de Cortesía Nocturna (Encendido sostenido 3s)..."));
  digitalWrite(PIN_LED_WHITE, HIGH);
  delay(3000);
  digitalWrite(PIN_LED_WHITE, LOW);

  Serial.println(F("[OK] Prueba de LEDs finalizada con éxito."));
  lcdShow(F("TEST LEDS       "), F("Finalizado OK   "));
}

void probarReleCompleto() {
  Serial.println(F("\n--- [PRUEBA 5: MÓDULO RELÉ (D7)] ---"));
  Serial.println(F("Nota: Escucha el chasquido 'CLICK' metálico del conmutador mecánico."));
  lcdShow(F("TEST RELE D7    "), F("Activando...    "));

  Serial.println(F(" 1. Activando Relé (ON - Habitación energizada)..."));
  digitalWrite(PIN_RELAY, HIGH);
  delay(2000);

  Serial.println(F(" 2. Desactivando Relé (OFF - Corte de energía general)..."));
  digitalWrite(PIN_RELAY, LOW);
  delay(1000);

  Serial.println(F(" 3. Prueba de Ciclos Rápidos (3 conmutaciones)..."));
  for (int i = 1; i <= 3; i++) {
    Serial.print(F("    - Ciclo ")); Serial.println(i);
    digitalWrite(PIN_RELAY, HIGH);
    delay(400);
    digitalWrite(PIN_RELAY, LOW);
    delay(400);
  }

  Serial.println(F("[OK] Prueba de relé completada."));
  lcdShow(F("TEST RELE D7    "), F("Finalizado OK   "));
}

void probarLCDCompleto() {
  Serial.println(F("\n--- [PRUEBA 6: PANTALLA LCD 1602 I2C] ---"));
  if (!lcdDetected) {
    bool ok = initLcdIfPresent();
    if (!ok) {
      Serial.println(F("[ERROR] Pantalla LCD no detectada en bus I2C (0x27 / 0x3F)."));
      Serial.println(F("Verifique los cables SDA (A4), SCL (A5), VCC (5V) y GND."));
      return;
    }
  }

  Serial.println(F(" 1. Escribiendo mensajes en pantalla..."));
  lcdShow(F(" HospedaSmart   "), F(" Habitacion 101 "));
  delay(2000);

  lcdShow(F("Estado: LIBRE   "), F("Clima: CONFORT  "));
  delay(2000);

  Serial.println(F(" 2. Probando retroiluminación (Backlight parpadeo 3 veces)..."));
  for (int i = 0; i < 3; i++) {
    activeLcd->noBacklight();
    delay(300);
    activeLcd->backlight();
    delay(300);
  }

  Serial.println(F(" 3. Demostración de contador en tiempo real..."));
  for (int count = 5; count >= 1; count--) {
    activeLcd->clear();
    activeLcd->setCursor(0, 0);
    activeLcd->print(F("Prueba LCD OK:"));
    activeLcd->setCursor(0, 1);
    activeLcd->print(F("Cuenta: "));
    activeLcd->print(count);
    activeLcd->print(F(" seg"));
    delay(700);
  }

  lcdShow(F(" HospedaSmart   "), F(" Test Completo! "));
  Serial.println(F("[OK] Prueba de LCD finalizada con éxito."));
}

// =====================================================================================
// PRUEBAS DE SENSORES Y CALIBRACIÓN
// =====================================================================================

void leerSensoresPuntual() {
  int rawLdr   = analogRead(PIN_LDR);
  int rawSteam = analogRead(PIN_STEAM);
  int rawGas   = analogRead(PIN_GAS_MQ2);
  int valPir   = digitalRead(PIN_PIR);
  int valBtn   = digitalRead(PIN_BUTTON);

  int mvLdr   = (int)(((long)rawLdr * 5000L) / 1023L);
  int mvGas   = (int)(((long)rawGas * 5000L) / 1023L);
  int mvSteam = (int)(((long)rawSteam * 5000L) / 1023L);

  Serial.println(F("------------------------------------------------------------------"));
  Serial.println(F(" REPORTE INSTANTÁNEO DE SENSORES:"));

  // Luz LDR
  Serial.print(F("  - LUZ (LDR A0)       : ADC=")); Serial.print(rawLdr);
  Serial.print(F(" (")); Serial.print(mvLdr / 1000); Serial.print(F("."));
  Serial.print((mvLdr % 1000) / 100); Serial.print(F("V) -> "));
  if (rawLdr < 300)      Serial.println(F("[NOCHE / OSCURIDAD]"));
  else if (rawLdr < 700) Serial.println(F("[LUZ DE HABITACION]"));
  else                   Serial.println(F("[LUZ SOLAR / ALTA]"));

  // Gas MQ-2
  Serial.print(F("  - GAS MQ-2 (A2)      : ADC=")); Serial.print(rawGas);
  Serial.print(F(" (")); Serial.print(mvGas / 1000); Serial.print(F("."));
  Serial.print((mvGas % 1000) / 100); Serial.print(F("V) -> "));
  if (rawGas > 450)      Serial.println(F("[!PELIGRO: FUGA DE GAS / HUMO!]"));
  else if (rawGas > 300) Serial.println(F("[PRECAUCIÓN: Nivel Moderado]"));
  else                   Serial.println(F("[Aire Limpio / Seguro]"));

  // Lluvia / Vapor
  Serial.print(F("  - VAPOR/LLUVIA (A1)  : ADC=")); Serial.print(rawSteam);
  Serial.print(F(" (")); Serial.print(mvSteam / 1000); Serial.print(F("."));
  Serial.print((mvSteam % 1000) / 100); Serial.print(F("V) -> "));
  if (rawSteam > 400)      Serial.println(F("[GOTAS DE AGUA / MOJADO]"));
  else if (rawSteam > 100) Serial.println(F("[Humedad / Vapor detectado]"));
  else                     Serial.println(F("[Superficie Seca]"));

  // Movimiento PIR
  Serial.print(F("  - MOVIMIENTO PIR (D2): "));
  if (millis() < 30000) {
    Serial.print(valPir == HIGH ? F("DETECTADO (Calibrando sensor...)") : F("Sin presencia (Calibrando...)"));
    Serial.println(F(" [PIR requiere ~30s tras encender]"));
  } else {
    Serial.println(valPir == HIGH ? F("PRESENCIA DETECTADA") : F("Habitacion Despejada"));
  }

  // Pulsador
  Serial.print(F("  - BOTÓN FÍSICO (D4)  : "));
  Serial.println(valBtn == LOW ? F("PRESIONADO [Activo]") : F("Libre [Reposo]"));
  Serial.println(F("------------------------------------------------------------------"));

  if (activeLcd) {
    activeLcd->clear();
    activeLcd->setCursor(0, 0);
    activeLcd->print(F("L:")); activeLcd->print(rawLdr);
    activeLcd->print(F(" G:")); activeLcd->print(rawGas);
    activeLcd->print(F(" V:")); activeLcd->print(rawSteam);
    activeLcd->setCursor(0, 1);
    activeLcd->print(F("PIR:")); activeLcd->print(valPir == HIGH ? F("SI ") : F("NO "));
    activeLcd->print(F("BTN:")); activeLcd->print(valBtn == LOW ? F("ON ") : F("OFF"));
  }
}

void enviarDatosPlotter() {
  int rawLdr   = analogRead(PIN_LDR);
  int rawGas   = analogRead(PIN_GAS_MQ2);
  int rawSteam = analogRead(PIN_STEAM);
  int valPir   = digitalRead(PIN_PIR) * 300;     // Escala visual
  int valBtn   = (digitalRead(PIN_BUTTON) == LOW ? 200 : 0);

  Serial.print(rawLdr);
  Serial.print(F(","));
  Serial.print(rawGas);
  Serial.print(F(","));
  Serial.print(rawSteam);
  Serial.print(F(","));
  Serial.print(valPir);
  Serial.print(F(","));
  Serial.println(valBtn);
}

void calibrarSensoresADC() {
  Serial.println(F("\n--- [MODO CALIBRACIÓN Y RANGO DINÁMICO (10 SEGUNDOS)] ---"));
  Serial.println(F("Instrucciones:"));
  Serial.println(F(" - Cubre y destapa el sensor LDR con la mano."));
  Serial.println(F(" - Acerca vapor de agua o gas de encendedor (sin llama) al MQ-2."));
  Serial.println(F("Muestreando en tiempo real...\n"));
  lcdShow(F("CALIBRANDO ADC.."), F("Tapa/acerca gas "));

  int minLdr = 1023, maxLdr = 0; long sumLdr = 0;
  int minGas = 1023, maxGas = 0; long sumGas = 0;
  int minStm = 1023, maxStm = 0; long sumStm = 0;
  int samples = 0;

  unsigned long startCal = millis();
  while (millis() - startCal < 10000) {
    int vL = analogRead(PIN_LDR);
    int vG = analogRead(PIN_GAS_MQ2);
    int vS = analogRead(PIN_STEAM);

    if (vL < minLdr) minLdr = vL;
    if (vL > maxLdr) maxLdr = vL;
    sumLdr += vL;

    if (vG < minGas) minGas = vG;
    if (vG > maxGas) maxGas = vG;
    sumGas += vG;

    if (vS < minStm) minStm = vS;
    if (vS > maxStm) maxStm = vS;
    sumStm += vS;

    samples++;
    delay(50);
  }

  int avgLdr = sumLdr / samples;
  int avgGas = sumGas / samples;
  int avgStm = sumStm / samples;

  Serial.println(F("=================================================================="));
  Serial.println(F(" INFORME DE CALIBRACIÓN DE RANGO DINÁMICO:"));
  Serial.println(F("=================================================================="));
  
  Serial.print(F(" 1. FOTORRESISTENCIA (LDR A0):\n    Min: ")); Serial.print(minLdr);
  Serial.print(F(" | Max: ")); Serial.print(maxLdr);
  Serial.print(F(" | Prom: ")); Serial.print(avgLdr);
  Serial.print(F(" | Rango Dinamico: ")); Serial.print(maxLdr - minLdr);
  Serial.println((maxLdr - minLdr) > 50 ? F(" -> [RESPUESTA ÓPTIMA]") : F(" -> [POCA VARIACIÓN]"));

  Serial.print(F(" 2. SENSOR DE GAS (MQ-2 A2):\n    Min: ")); Serial.print(minGas);
  Serial.print(F(" | Max: ")); Serial.print(maxGas);
  Serial.print(F(" | Prom: ")); Serial.print(avgGas);
  Serial.print(F(" | Rango Dinamico: ")); Serial.print(maxGas - minGas);
  Serial.println(avgGas > 50 ? F(" -> [SENSOR OPERATIVO]") : F(" -> [VERIFICAR ALIMENTACIÓN]"));

  Serial.print(F(" 3. SENSOR DE VAPOR/LLUVIA (A1):\n    Min: ")); Serial.print(minStm);
  Serial.print(F(" | Max: ")); Serial.print(maxStm);
  Serial.print(F(" | Prom: ")); Serial.print(avgStm);
  Serial.print(F(" | Rango Dinamico: ")); Serial.println(maxStm - minStm);
  Serial.println(F("=================================================================="));

  lcdShow(F("CALIBRACION OK  "), F("Ver Monitor Ser "));
}

void probarBotonInteractivo() {
  Serial.println(F("\n--- [PRUEBA INTERACTIVA DE BOTÓN FÍSICO D4] ---"));
  Serial.println(F("Presiona el botón en la maqueta (durante 15 segundos):"));
  Serial.println(F(" - Pulsación Corta (< 1s): Bip simple de click."));
  Serial.println(F(" - Pulsación Larga (> 1.5s): Tono doble (Cambio de estado de servicio)."));
  Serial.println(F("Iniciando prueba...\n"));
  lcdShow(F("TEST BOTON D4   "), F("Presione boton.."));

  unsigned long startTime = millis();
  int clickCount = 0;
  bool lastState = HIGH;
  unsigned long pressStart = 0;

  while (millis() - startTime < 15000) {
    bool currentState = digitalRead(PIN_BUTTON);

    // Detección de flanco de bajada (Presión con INPUT_PULLUP)
    if (lastState == HIGH && currentState == LOW) {
      pressStart = millis();
      tone(PIN_BUZZER, 2000, 30);
    }
    // Detección de flanco de subida (Liberación)
    else if (lastState == LOW && currentState == HIGH) {
      unsigned long duration = millis() - pressStart;
      clickCount++;

      Serial.print(F(" -> Click #")); Serial.print(clickCount);
      Serial.print(F(" | Duración: ")); Serial.print(duration); Serial.print(F(" ms -> "));

      if (duration >= 1500) {
        Serial.println(F("[PULSACIÓN LARGA DETECTADA: Cambio de Modo]"));
        tone(PIN_BUZZER, 2400, 150); delay(170);
        tone(PIN_BUZZER, 2800, 200);
      } else {
        Serial.println(F("[PULSACIÓN CORTA: Selección estándar]"));
      }
    }
    lastState = currentState;
    delay(10);
  }

  Serial.print(F("\n[FIN DE PRUEBA] Total de pulsaciones registradas: "));
  Serial.println(clickCount);
  lcdShow(F("TEST BOTON D4   "), F("Finalizado OK   "));
}

void probarSensorPIR() {
  Serial.println(F("\n--- [PRUEBA DE SENSOR DE MOVIMIENTO PIR D2] ---"));
  Serial.println(F("Monitoreando presencia durante 15 segundos..."));
  Serial.println(F("Mueve tu mano frente al domo del PIR."));
  lcdShow(F("TEST SENSOR PIR "), F("Mueva la mano..."));

  unsigned long startTime = millis();
  int lastVal = LOW;
  unsigned long motionStart = 0;
  int eventCount = 0;

  while (millis() - startTime < 15000) {
    int val = digitalRead(PIN_PIR);
    if (val == HIGH && lastVal == LOW) {
      eventCount++;
      motionStart = millis();
      digitalWrite(PIN_LED_WHITE, HIGH);
      tone(PIN_BUZZER, 1800, 50);
      Serial.print(F(" [")); Serial.print((millis() - startTime) / 1000);
      Serial.println(F("s] -> !MOVIMIENTO DETECTADO! (LED Blanco ON)"));
      lcdShow(F("PIR: DETECTADO! "), F("Persona presente"));
    } else if (val == LOW && lastVal == HIGH) {
      unsigned long duration = (millis() - motionStart) / 1000;
      digitalWrite(PIN_LED_WHITE, LOW);
      Serial.print(F(" [")); Serial.print((millis() - startTime) / 1000);
      Serial.print(F("s] -> Presencia finalizada. Duración: "));
      Serial.print(duration); Serial.println(F(" segundos."));
      lcdShow(F("PIR: Despejado  "), F("Sin movimiento  "));
    }
    lastVal = val;
    delay(50);
  }

  digitalWrite(PIN_LED_WHITE, LOW);
  Serial.print(F("\n[FIN DE PRUEBA] Eventos de presencia detectados: "));
  Serial.println(eventCount);
  lcdShow(F("TEST SENSOR PIR "), F("Finalizado OK   "));
}

void escanearI2CExhaustivo() {
  Serial.println(F("\n--- [ESCÁNER EXHAUSTIVO DE BUS I2C (Pines A4/A5)] ---"));
  byte count = 0;
  for (byte address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    byte error = Wire.endTransmission();
    if (error == 0) {
      Serial.print(F(" -> Dispositivo encontrado en HEX: 0x"));
      if (address < 16) Serial.print(F("0"));
      Serial.print(address, HEX);
      if (address == 0x27 || address == 0x3F) {
        Serial.print(F(" (Direccion tipica LCD 1602 I2C)"));
      } else if (address == 0x68) {
        Serial.print(F(" (Modulo Reloj RTC DS3231 / DS1307)"));
      }
      Serial.println();
      count++;
    }
  }
  if (count == 0) {
    Serial.println(F("[ALERTA] No se detecto ningun dispositivo en el bus I2C."));
  } else {
    Serial.print(F("[OK] Escaneo completado. Total dispositivos encontrados: "));
    Serial.println(count);
  }
}

// =====================================================================================
// SIMULACIÓN DE ESCENARIOS HOSPEDASMART
// =====================================================================================

void simularControlAcceso() {
  Serial.println(F("\n=== [SIMULACIÓN ESCENARIO 1: CONTROL DE ACCESO] ==="));
  Serial.println(F("Ingrese el PIN de prueba en el Monitor Serial y presione ENTER:"));
  Serial.println(F(" (PIN Correcto: 1234 | Cualquier otro: Denegado)"));
  lcdShow(F("CONTROL ACCESO  "), F("Ingrese su PIN.."));

  while (Serial.available() > 0) Serial.read(); // Limpiar buffer

  while (Serial.available() == 0) {
    ; // Esperar entrada
  }

  String enteredPin = Serial.readStringUntil('\n');
  enteredPin.trim();

  if (enteredPin == "1234") {
    Serial.println(F("[ACCESO CONCEDIDO] PIN '1234' Valido."));
    Serial.println(F(" -> Abriendo cerrojo (Servomotor a 90 grados)..."));
    doorServo.write(90);

    tone(PIN_BUZZER, 1800, 100); delay(120);
    tone(PIN_BUZZER, 2400, 180);

    lcdShow(F("Acceso Valido   "), F("Bienvenido!     "));

    Serial.println(F(" -> Manteniendo puerta abierta durante 5 segundos..."));
    for (int s = 5; s >= 1; s--) {
      Serial.print(F("    Cerrando en: ")); Serial.print(s); Serial.println(F("s"));
      delay(1000);
    }

    Serial.println(F(" -> Bloqueando cerrojo (Servomotor a 0 grados)..."));
    doorServo.write(0);
    lcdShow(F("Puerta Cerrada  "), F("Cerrojo Bloquead"));
  } else {
    Serial.print(F("[ACCESO DENEGADO] Clave ingresada incorrecta: "));
    Serial.println(enteredPin);
    tone(PIN_BUZZER, 400, 600);
    lcdShow(F("PIN Incorrecto! "), F("Acceso Denegado "));
  }
  delay(1500);
  Serial.println(F("=== [FIN DE SIMULACIÓN ACCESO] ==="));
}

void simularEmergenciaGas() {
  Serial.println(F("\n=== [SIMULACIÓN ESCENARIO 2: ALERTA CRÍTICA DE GAS MQ-2] ==="));
  Serial.println(F("Disparando protocolo de evacuación automática durante 6 segundos:"));
  Serial.println(F(" 1. Extractor de aire (Ventilador L9110) al 100%."));
  Serial.println(F(" 2. Sirena acústica continua en Zumbador (D3)."));
  Serial.println(F(" 3. Alarma luminosa estroboscópica con LED Amarillo (D12)."));
  Serial.println(F(" 4. Mensaje de emergencia en pantalla LCD 1602."));

  lcdShow(F("!PELIGRO: GAS!  "), F("EVACUAR EL AREA "));

  // Activar ventilador
  digitalWrite(PIN_FAN_INA, HIGH);
  digitalWrite(PIN_FAN_INB, LOW);

  unsigned long alarmStart = millis();
  bool ledState = false;
  while (millis() - alarmStart < 6000) {
    ledState = !ledState;
    digitalWrite(PIN_LED_YELLOW, ledState ? HIGH : LOW);
    tone(PIN_BUZZER, ledState ? 2200 : 1600, 100);
    delay(100);
  }

  // Normalizar sistema
  digitalWrite(PIN_FAN_INA, LOW);
  digitalWrite(PIN_FAN_INB, LOW);
  digitalWrite(PIN_LED_YELLOW, LOW);
  noTone(PIN_BUZZER);

  Serial.println(F("\n[SISTEMA NORMALIZADO] Ventilador apagado y alarma silenciada."));
  lcdShow(F("Gas Normalizado "), F("Area Segura     "));
  delay(1500);
  Serial.println(F("=== [FIN DE SIMULACIÓN GAS] ==="));
}

void simularConfortLuz() {
  Serial.println(F("\n=== [SIMULACIÓN ESCENARIO 3: CONFORT Y AHORRO LUMÍNICO] ==="));
  Serial.println(F("Leyendo nivel de luz ambiental (LDR A0)..."));

  int currentLdr = analogRead(PIN_LDR);
  Serial.print(F(" -> Nivel de luz actual: ")); Serial.print(currentLdr);

  if (currentLdr < 400) {
    Serial.println(F(" [CONDICIÓN NOCTURNA CUMPLIDA]"));
    Serial.println(F(" -> Huésped detectado: Encendiendo Luz de Cortesía (LED Blanco D13)..."));
    digitalWrite(PIN_LED_WHITE, HIGH);
    lcdShow(F("Luz Cortesía ON "), F("Noche Detectada "));
    delay(4000);
    digitalWrite(PIN_LED_WHITE, LOW);
    Serial.println(F(" -> Tiempo de estancia agotado: Apagando luz para ahorrar energía."));
    lcdShow(F("Luz Cortesía OFF"), F("Ahorro Activo   "));
  } else {
    Serial.println(F(" [HAY SUFICIENTE LUZ DE DÍA]"));
    Serial.println(F(" -> El sistema NO enciende el LED blanco para evitar consumo innecesario."));
    lcdShow(F("Luz Dia Adecuada"), F("Ahorro de Luz OK"));
  }
  delay(1500);
  Serial.println(F("=== [FIN DE SIMULACIÓN CONFORT] ==="));
}

// =====================================================================================
// AUTO-TEST COMPLETO (Secuencia automática)
// =====================================================================================

void ejecutarAutoTestCompleto() {
  Serial.println(F("\n=================================================================="));
  Serial.println(F("     INICIANDO AUTO-TEST COMPLETO DE FÁBRICA (HOSPEDASMART)       "));
  Serial.println(F("=================================================================="));

  // 1. LEDs
  lcdShow(F("AUTO-TEST 1/6   "), F("Prueba de LEDs  "));
  Serial.println(F("[1/6] Verificando LEDs..."));
  digitalWrite(PIN_LED_WHITE, HIGH); delay(400); digitalWrite(PIN_LED_WHITE, LOW);
  digitalWrite(PIN_LED_YELLOW, HIGH); delay(400); digitalWrite(PIN_LED_YELLOW, LOW);

  // 2. Buzzer
  lcdShow(F("AUTO-TEST 2/6   "), F("Prueba de Buzzer"));
  Serial.println(F("[2/6] Verificando Zumbador..."));
  tone(PIN_BUZZER, 2000, 100); delay(120);
  tone(PIN_BUZZER, 2500, 150); delay(200);

  // 3. Relé
  lcdShow(F("AUTO-TEST 3/6   "), F("Prueba de Rele  "));
  Serial.println(F("[3/6] Verificando Relé (Click ON -> OFF)..."));
  digitalWrite(PIN_RELAY, HIGH); delay(800);
  digitalWrite(PIN_RELAY, LOW);  delay(400);

  // 4. Servomotor
  lcdShow(F("AUTO-TEST 4/6   "), F("Prueba Servomotor"));
  Serial.println(F("[4/6] Verificando Servomotor (0 -> 90 -> 0)..."));
  doorServo.write(90); delay(1000);
  doorServo.write(0);  delay(600);

  // 5. Ventilador L9110
  lcdShow(F("AUTO-TEST 5/6   "), F("Prueba Ventilado"));
  Serial.println(F("[5/6] Verificando Ventilador (Giro rápido 1s)..."));
  digitalWrite(PIN_FAN_INA, HIGH);
  digitalWrite(PIN_FAN_INB, LOW);
  delay(1200);
  digitalWrite(PIN_FAN_INA, LOW);
  digitalWrite(PIN_FAN_INB, LOW);

  // 6. Lectura diagnóstica de sensores
  lcdShow(F("AUTO-TEST 6/6   "), F("Leyendo Sensores"));
  Serial.println(F("[6/6] Leyendo sensores y evaluando conectividad..."));
  leerSensoresPuntual();

  Serial.println(F("\n=================================================================="));
  Serial.println(F(" [AUTO-TEST FINALIZADO] Todos los subsistemas fueron evaluados.  "));
  Serial.println(F("=================================================================="));
  lcdShow(F("AUTO-TEST OK!   "), F("Todo Operativo  "));
}
