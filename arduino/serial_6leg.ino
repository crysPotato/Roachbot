/*
  arduino/serial_6leg.ino
  ────────────────────────
  Drop-in addition to your RoachBotV2 sketch.
  Adds 6 independent encoders (one per leg) and sends the
  canonical serial format that the Python visualizer expects.

  CANONICAL OUTPUT FORMAT (one line per report interval):
    ENC:FL=120,ML=80,RL=45,FR=100,MR=60,RR=30\n

  ─── WIRING (suggested GPIO — adjust to your board) ─────────
  Leg   Motor IN1  IN2   Enc A   Enc B
  FL    GPIO 26   27    GPIO 34  35    ← your current LEFT test
  ML    GPIO 14   12    GPIO 36  39
  RL    GPIO 13   15    GPIO 25  26*   (* avoid if using SPI)
  FR    GPIO 16   17    GPIO 32  33    ← your current RIGHT test
  MR    GPIO 18   19    GPIO 22  23
  RR    GPIO 21    4    GPIO  5   2*   (* boot-strap issues on some boards)

  ─── HOW TO INTEGRATE ────────────────────────────────────────
  1. Extend your existing encoder ISR pattern for all 6 legs.
  2. Call reportEncoders() from inside your main loop at
     whatever rate you want (the visualizer handles variable rates).
  3. The visualizer also parses your existing test format:
       [LEFT 0->180] Lseg=120/234  (92.3 deg)
     so you can test with your current sketch immediately.
*/

#include <Arduino.h>

// ─── Leg indices ─────────────────────────────────────────────
#define LEG_FL 0
#define LEG_ML 1
#define LEG_RL 2
#define LEG_FR 3
#define LEG_MR 4
#define LEG_RR 5
#define NUM_LEGS 6

// ─── Encoder pin pairs [A, B] ─────────────────────────────────
static const int ENC_PINS[NUM_LEGS][2] = {
  {34, 35},   // FL  ← your existing LEFT encoder
  {36, 39},   // ML  (input-only pins, no ISR on GPIO39 — use polling or remap)
  {25, 27},   // RL
  {32, 33},   // FR  ← your existing RIGHT encoder
  {22, 23},   // MR
  {5,  2},    // RR
};

// ─── Encoder counts (volatile: written by ISR, read by loop) ──
volatile long legCount[NUM_LEGS] = {0};

// ─── Direction flags (set in your motion controller) ──────────
// +1 = forward counts increase, -1 = reversed wiring compensation
const int ENC_DIR[NUM_LEGS] = {
  -1,   // FL  ← your LEFT_ENCODER_REVERSED = true
   1,   // ML
   1,   // RL
   1,   // FR
   1,   // MR
   1,   // RR
};

// ─── ISR factory macro ────────────────────────────────────────
// For each leg, we need two ISRs (channel A and B).
// Quadrature decode identical to your existing code.
#define MAKE_ISR(IDX, PIN_A, PIN_B)                         \
  void IRAM_ATTR isrLeg##IDX##A() {                         \
    bool a = digitalRead(PIN_A);                            \
    bool b = digitalRead(PIN_B);                            \
    legCount[IDX] += (a == b) ? ENC_DIR[IDX] : -ENC_DIR[IDX]; \
  }                                                         \
  void IRAM_ATTR isrLeg##IDX##B() {                         \
    bool a = digitalRead(PIN_A);                            \
    bool b = digitalRead(PIN_B);                            \
    legCount[IDX] += (a != b) ? ENC_DIR[IDX] : -ENC_DIR[IDX]; \
  }

MAKE_ISR(0, 34, 35)
MAKE_ISR(1, 36, 39)
MAKE_ISR(2, 25, 27)
MAKE_ISR(3, 32, 33)
MAKE_ISR(4, 22, 23)
MAKE_ISR(5,  5,  2)

// ISR function pointers for attachInterrupt
void (*isrA[NUM_LEGS])() = {
  isrLeg0A, isrLeg1A, isrLeg2A, isrLeg3A, isrLeg4A, isrLeg5A
};
void (*isrB[NUM_LEGS])() = {
  isrLeg0B, isrLeg1B, isrLeg2B, isrLeg3B, isrLeg4B, isrLeg5B
};

// ─── Safe count reader ────────────────────────────────────────
long getCount(int leg) {
  noInterrupts();
  long c = legCount[leg];
  interrupts();
  return c;
}

void resetAllCounts() {
  noInterrupts();
  for (int i = 0; i < NUM_LEGS; i++) legCount[i] = 0;
  interrupts();
}

// ─── Serial report ────────────────────────────────────────────
// Call this from loop() at whatever rate suits your application.
// Output: ENC:FL=120,ML=80,RL=45,FR=100,MR=60,RR=30
static const char* LEG_NAMES[] = {"FL","ML","RL","FR","MR","RR"};

void reportEncoders() {
  Serial.print("ENC:");
  for (int i = 0; i < NUM_LEGS; i++) {
    Serial.print(LEG_NAMES[i]);
    Serial.print("=");
    Serial.print(getCount(i));
    if (i < NUM_LEGS - 1) Serial.print(",");
  }
  Serial.println();
}

// ─── Setup / Loop stubs (merge into your existing sketch) ─────
void setup6LegEncoders() {
  for (int i = 0; i < NUM_LEGS; i++) {
    pinMode(ENC_PINS[i][0], INPUT);
    pinMode(ENC_PINS[i][1], INPUT);
    attachInterrupt(digitalPinToInterrupt(ENC_PINS[i][0]), isrA[i], CHANGE);
    // GPIO 36 & 39 do NOT support interrupts on ESP32 — use polling for ML
    if (ENC_PINS[i][0] != 36 && ENC_PINS[i][0] != 39) {
      attachInterrupt(digitalPinToInterrupt(ENC_PINS[i][1]), isrB[i], CHANGE);
    }
  }
}

/*
  In your setup():
    setup6LegEncoders();
    Serial.begin(115200);

  In your loop():
    // ... your motion control code ...
    reportEncoders();            // send every loop iteration, or
    // reportEncoders() every N ms:
    static unsigned long lastReport = 0;
    if (millis() - lastReport >= 50) {   // 20 Hz
      reportEncoders();
      lastReport = millis();
    }
*/
