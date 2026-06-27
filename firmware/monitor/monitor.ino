// PC + Claude monitor for GUITION ESP32-2424S012 (ESP32-C3 + 1.28" round GC9A01)
// Lines over USB-serial (COM5 @115200), '\n' terminated:
//   cpu=37.5 ram=61.2 sess=26 week=56 sessp=44 weekp=99 sessh=2.8 weekh=8
//   cpu/ram=PC%, sess/week=Claude session/week %, sessp/weekp=period elapsed %,
//   sessh/weekh=hours left in each window. Unknown keys ignored.
//
// UI: short TAP toggles page (Page0 CPU/RAM, Page1 Session/Week + period bars).
//     LONG press (>0.6s) rotates 90 deg. White tick marks each gauge's 0/start
//     (drawn in the gap between rings so it never flickers).
//
// Rendering: rings drawn directly; center text+bars via a small sprite. (Full-
// screen double-buffering was tried and would not display on this panel.)
//
// Pinout: LCD SCLK=6 MOSI=7 DC=2 CS=10 RST=none BL=3 · Touch CST816 @0x15 SDA=4 SCL=5 INT=0 RST=1
// FQBN: esp32:esp32:esp32c3:CDCOnBoot=cdc,FlashSize=4M

#include <LovyanGFX.hpp>
#include <Wire.h>

class LGFX : public lgfx::LGFX_Device {
  lgfx::Panel_GC9A01 _panel; lgfx::Bus_SPI _bus;
public:
  LGFX() {
    { auto c = _bus.config();
      c.spi_host = SPI2_HOST; c.spi_mode = 0; c.freq_write = 40000000; c.freq_read = 16000000;
      c.pin_sclk = 6; c.pin_mosi = 7; c.pin_miso = -1; c.pin_dc = 2;
      _bus.config(c); _panel.setBus(&_bus); }
    { auto c = _panel.config();
      c.pin_cs = 10; c.pin_rst = -1; c.pin_busy = -1;
      c.panel_width = 240; c.panel_height = 240; c.invert = true; c.rgb_order = false;
      _panel.config(c); }
    setPanel(&_panel);
  }
};

LGFX tft;
static LGFX_Sprite center(&tft);      // small canvas for the center readout

static const int PIN_BL = 3;
static const int CX = 120, CY = 120;

static const int OUT_R0 = 96,  OUT_R1 = 110;   // outer thick ring (this page, metric 1)
static const int IN_R0  = 76,  IN_R1  = 90;     // inner thick ring (this page, metric 2)
static const int TA_R0  = 117, TA_R1  = 119;    // outer thin ring (other page, metric 1)
static const int TB_R0  = 113, TB_R1  = 115;    // 2nd thin ring   (other page, metric 2)
static const int TICK_R0 = 91, TICK_R1 = 95;    // zero tick lives in the ring gap
static const float START_DEG = 0.0f;

static const int TP_SDA = 4, TP_SCL = 5, TP_INT = 0, TP_RST = 1;
static const uint8_t CST816_ADDR = 0x15;
static const uint32_t LONG_MS = 600;
uint8_t rotation = 0, page = 0;
bool tpWasDown = false, tpFired = false;
uint32_t tpPressStart = 0;

float cpuTarget=0, ramTarget=0, sessTarget=0, weekTarget=0;
float cpuDisp=0,  ramDisp=0,  sessDisp=0,  weekDisp=0;
bool sessHave=false, weekHave=false;
float sesspTarget=-1, weekpTarget=-1, sesshVal=-1, weekhVal=-1;
uint32_t lastData = 0;
bool everConnected = false;
String inbuf;

uint16_t zoneColor(float v) {
  if (v < 60) return tft.color565(0, 200, 90);
  if (v < 85) return tft.color565(255, 170, 0);
  return tft.color565(255, 60, 60);
}
static const uint16_t GRAY = 0x528A;

void parseLine(const String& line) {
  int i = 0;
  while (i < (int)line.length()) {
    int sp = line.indexOf(' ', i); if (sp < 0) sp = line.length();
    String tok = line.substring(i, sp); int eq = tok.indexOf('=');
    if (eq > 0) {
      String k = tok.substring(0, eq); float v = tok.substring(eq + 1).toFloat();
      if      (k == "cpu")   cpuTarget  = constrain(v, 0, 100);
      else if (k == "ram")   ramTarget  = constrain(v, 0, 100);
      else if (k == "sess")  { sessTarget = constrain(v, 0, 100); sessHave = true; }
      else if (k == "week")  { weekTarget = constrain(v, 0, 100); weekHave = true; }
      else if (k == "sessp") sesspTarget = constrain(v, 0, 100);
      else if (k == "weekp") weekpTarget = constrain(v, 0, 100);
      else if (k == "sessh") sesshVal = v;
      else if (k == "weekh") weekhVal = v;
    }
    i = sp + 1;
  }
  lastData = millis(); everConnected = true;
}

void readSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') { if (inbuf.length()) parseLine(inbuf); inbuf = ""; }
    else if (c != '\r') { inbuf += c; if (inbuf.length() > 200) inbuf = ""; }
  }
}

void touchReset() {
  pinMode(TP_RST, OUTPUT);
  digitalWrite(TP_RST, LOW);  delay(20);
  digitalWrite(TP_RST, HIGH); delay(120);
}
bool touchDown() {
  Wire.beginTransmission(CST816_ADDR); Wire.write(0x02);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((int)CST816_ADDR, 1) != 1) return false;
  return (Wire.read() & 0x0F) > 0;
}
void handleTouch() {
  bool down = touchDown();
  if (down && !tpWasDown) { tpPressStart = millis(); tpFired = false; }
  if (down && !tpFired && (millis() - tpPressStart) > LONG_MS) {
    rotation = (rotation + 1) & 0x03;
    tft.setRotation(rotation); tft.fillScreen(TFT_BLACK);
    Serial.printf("rotate -> %d\n", rotation); tpFired = true;
  }
  if (!down && tpWasDown) {
    if (!tpFired && (millis() - tpPressStart) < LONG_MS) {
      page = (page + 1) % 2; tft.fillScreen(TFT_BLACK);
      Serial.printf("page -> %d\n", page);
    }
    tpFired = false;
  }
  tpWasDown = down;
}

void drawRing(int r0, int r1, float val, uint16_t col) {
  float sweep = 360.0f * (val / 100.0f); if (sweep > 359.9f) sweep = 359.9f;
  tft.fillArc(CX, CY, r0, r1, START_DEG + sweep, START_DEG + 360.0f, tft.color565(35, 35, 40));
  if (sweep > 0.1f) tft.fillArc(CX, CY, r0, r1, START_DEG, START_DEG + sweep, col);
}
// thin zero tick in the inter-ring gap -> never overpainted, so it can't flicker
void drawStartTick() {
  tft.fillArc(CX, CY, TICK_R0, TICK_R1, START_DEG - 1.5f, START_DEG + 1.5f, TFT_WHITE);
}

void drawBar(int y, float frac, float hours) {       // inside the center sprite
  int bw = 40, bh = 3;
  // build the "Nh"/"Nd" hours-left label and measure it, so the bar+label group
  // can be centered as a unit
  String t = "";
  int tw = 0;
  if (hours >= 0) {
    t = (hours >= 48) ? String((int)round(hours / 24.0)) + "d"
                      : String((int)round(hours)) + "h";
    center.setFont(&fonts::Font0);
    tw = center.textWidth(t);
  }
  int gap = t.length() ? 5 : 0;
  int total = bw + gap + tw;
  int bx = center.width() / 2 - total / 2;          // center the whole group
  center.fillRect(bx, y, bw, bh, tft.color565(55, 55, 65));
  int fw = (int)round(bw * constrain(frac, 0, 100) / 100.0);
  if (fw > 0) center.fillRect(bx, y, fw, bh, TFT_WHITE);
  if (t.length()) {
    center.setFont(&fonts::Font0); center.setTextDatum(middle_left);
    center.setTextColor(tft.color565(150, 150, 160), TFT_BLACK);
    center.drawString(t, bx + bw + gap, y + 1);
  }
}

void drawCenter(bool waiting,
                const char* l1, float v1, bool v1ok,
                const char* l2, float v2, bool v2ok,
                float p1 = -1, float p2 = -1, float h1 = -1, float h2 = -1) {
  center.fillScreen(TFT_BLACK);
  const int w = center.width() / 2;
  const uint16_t label = tft.color565(150, 150, 160);
  center.setTextDatum(middle_center);
  if (waiting) {
    center.setFont(&fonts::Font2);
    center.setTextColor(tft.color565(120, 120, 120), TFT_BLACK);
    center.drawString("WAITING", w, w - 9);
    center.drawString("FOR PC",  w, w + 9);
  } else {
    center.setFont(&fonts::Font2); center.setTextColor(label, TFT_BLACK);
    center.drawString(l1, w, 14);
    center.setFont(&fonts::Font4); center.setTextColor(v1ok ? zoneColor(v1) : GRAY, TFT_BLACK);
    center.drawString(v1ok ? String((int)round(v1)) + "%" : "--", w, 33);
    if (p1 >= 0) drawBar(47, p1, h1);

    center.setTextDatum(middle_center);
    center.setFont(&fonts::Font2); center.setTextColor(label, TFT_BLACK);
    center.drawString(l2, w, 63);
    center.setFont(&fonts::Font4); center.setTextColor(v2ok ? zoneColor(v2) : GRAY, TFT_BLACK);
    center.drawString(v2ok ? String((int)round(v2)) + "%" : "--", w, 82);
    if (p2 >= 0) drawBar(96, p2, h2);
  }
  center.pushSprite(CX - center.width() / 2, CY - center.height() / 2);
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_BL, OUTPUT); digitalWrite(PIN_BL, HIGH);
  tft.init(); tft.setRotation(rotation); tft.fillScreen(TFT_BLACK);
  Wire.begin(TP_SDA, TP_SCL); Wire.setClock(100000); touchReset();
  center.setColorDepth(16); center.createSprite(104, 104);
  Serial.printf("monitor ready, free heap %u\n", ESP.getFreeHeap());
}

void loop() {
  readSerial();
  handleTouch();
  bool waiting = !everConnected || (millis() - lastData > 3000);

  float k = 0.18f;
  cpuDisp  += ((waiting ? 0 : cpuTarget)  - cpuDisp)  * k;
  ramDisp  += ((waiting ? 0 : ramTarget)  - ramDisp)  * k;
  sessDisp += ((waiting ? 0 : sessTarget) - sessDisp) * k;
  weekDisp += ((waiting ? 0 : weekTarget) - weekDisp) * k;

  static uint32_t lastFrame = 0;
  if (millis() - lastFrame < 33) return;
  lastFrame = millis();

  bool sOk = sessHave && !waiting, wOk = weekHave && !waiting, pOk = !waiting;
  if (page == 0) {
    drawRing(OUT_R0, OUT_R1, cpuDisp, pOk ? zoneColor(cpuDisp) : GRAY);
    drawRing(IN_R0,  IN_R1,  ramDisp, pOk ? zoneColor(ramDisp) : GRAY);
    drawRing(TA_R0,  TA_R1,  sessDisp, sOk ? zoneColor(sessDisp) : GRAY);
    drawRing(TB_R0,  TB_R1,  weekDisp, wOk ? zoneColor(weekDisp) : GRAY);
    drawStartTick();
    drawCenter(waiting, "CPU", cpuDisp, true, "RAM", ramDisp, true);
  } else {
    drawRing(OUT_R0, OUT_R1, sessDisp, sOk ? zoneColor(sessDisp) : GRAY);
    drawRing(IN_R0,  IN_R1,  weekDisp, wOk ? zoneColor(weekDisp) : GRAY);
    drawRing(TA_R0,  TA_R1,  cpuDisp,  pOk ? zoneColor(cpuDisp)  : GRAY);
    drawRing(TB_R0,  TB_R1,  ramDisp,  pOk ? zoneColor(ramDisp)  : GRAY);
    drawStartTick();
    drawCenter(waiting, "SESS", sessDisp, sOk, "WEEK", weekDisp, wOk,
               sOk ? sesspTarget : -1, wOk ? weekpTarget : -1,
               sOk ? sesshVal : -1,    wOk ? weekhVal : -1);
  }
}
