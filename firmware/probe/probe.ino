// Probe sketch for GUITION ESP32-2424S012 (ESP32-C3 + 1.28" round GC9A01 + CST816 touch)
// Goal: empirically confirm the documented pinout lights the screen.
//
// Pinout under test (from board docs):
//   LCD: SCLK=6  MOSI=7  DC=2  CS=10  RST=-1(none)  BL=3
//   Touch CST816 (I2C @0x15): SDA=4 SCL=5 INT=0 RST=1
//
// Build needs LovyanGFX. Serial uses USB CDC (FQBN flag CDCOnBoot=cdc).

#include <LovyanGFX.hpp>

class LGFX : public lgfx::LGFX_Device {
  lgfx::Panel_GC9A01 _panel;
  lgfx::Bus_SPI      _bus;
public:
  LGFX() {
    { auto c = _bus.config();
      c.spi_host   = SPI2_HOST;   // FSPI on the C3
      c.spi_mode   = 0;
      c.freq_write = 40000000;
      c.freq_read  = 16000000;
      c.pin_sclk   = 6;
      c.pin_mosi   = 7;
      c.pin_miso   = -1;
      c.pin_dc     = 2;
      _bus.config(c);
      _panel.setBus(&_bus);
    }
    { auto c = _panel.config();
      c.pin_cs   = 10;
      c.pin_rst  = -1;
      c.pin_busy = -1;
      c.panel_width   = 240;
      c.panel_height  = 240;
      c.offset_x = 0;
      c.offset_y = 0;
      c.readable   = false;
      c.invert     = true;   // GC9A01 wants inversion on
      c.rgb_order  = false;
      c.dlen_16bit = false;
      c.bus_shared = false;
      _panel.config(c);
    }
    setPanel(&_panel);
  }
};

LGFX tft;

static const int PIN_BL = 3;

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println();
  Serial.println("=== ESP32-2424S012 PROBE ===");

  // Step 1: backlight test — blink 3x so you can see GPIO3 controls the panel light
  pinMode(PIN_BL, OUTPUT);
  for (int i = 0; i < 3; i++) {
    Serial.printf("backlight ON  (GPIO%d)\n", PIN_BL);
    digitalWrite(PIN_BL, HIGH); delay(350);
    Serial.println("backlight OFF");
    digitalWrite(PIN_BL, LOW);  delay(250);
  }
  digitalWrite(PIN_BL, HIGH);   // leave it on

  // Step 2: bring up the GC9A01
  Serial.println("init GC9A01...");
  tft.init();
  tft.setRotation(0);

  // color flood so you can confirm pixels are real
  tft.fillScreen(TFT_RED);   delay(400);
  tft.fillScreen(TFT_GREEN); delay(400);
  tft.fillScreen(TFT_BLUE);  delay(400);
  tft.fillScreen(TFT_BLACK);

  // centered round-display test pattern
  int cx = 120, cy = 120;
  for (int r = 118; r > 0; r -= 12)
    tft.drawCircle(cx, cy, r, tft.color565(0, 180, 255));
  tft.drawFastHLine(0, cy, 240, TFT_DARKGREY);
  tft.drawFastVLine(cx, 0, 240, TFT_DARKGREY);

  tft.setTextDatum(middle_center);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextSize(2);
  tft.drawString("PROBE OK", cx, cy - 18);
  tft.setTextSize(1);
  tft.drawString("ESP32-2424S012", cx, cy + 12);
  tft.drawString("240x240 GC9A01", cx, cy + 30);

  Serial.println("display init done -> you should see 'PROBE OK'");
}

void loop() {
  // heartbeat: small sweeping arc + serial tick so we know it's alive
  static int a = 0;
  static uint32_t last = 0;
  if (millis() - last > 40) {
    last = millis();
    float rad = a * 3.14159265f / 180.0f;
    int x = 120 + (int)(60 * cosf(rad));
    int y = 120 + (int)(60 * sinf(rad));
    tft.fillCircle(x, y, 4, TFT_YELLOW);
    tft.fillCircle(120 + (int)(60 * cosf((a - 12) * 3.14159265f / 180.0f)),
                   120 + (int)(60 * sinf((a - 12) * 3.14159265f / 180.0f)), 4, TFT_BLACK);
    a = (a + 6) % 360;
    if (a == 0) Serial.println("alive");
  }
}
