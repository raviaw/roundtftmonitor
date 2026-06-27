// I2C bus scanner for ESP32-2424S012 — find every device on the touch/IMU bus.
// Touch CST816 is on SDA=4 SCL=5. A 6-axis IMU (gyro+accel), if populated, would
// also be here: QMI8658=0x6A/0x6B, MPU6050=0x68/0x69, LSM6=0x6A/0x6B, BMI=0x68/0x69.

#include <Wire.h>

void setup() {
  Serial.begin(115200);
  delay(400);
  Wire.begin(4, 5);          // SDA=4, SCL=5
  Wire.setClock(100000);
  Serial.println();
  Serial.println("=== I2C SCAN (SDA=4 SCL=5) ===");
}

void loop() {
  int found = 0;
  for (uint8_t a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) {
      found++;
      Serial.printf("found 0x%02X", a);
      if (a == 0x15) Serial.print("  -> CST816 touch");
      else if (a == 0x68 || a == 0x69) Serial.print("  -> MPU6050/BMI-class IMU (gyro)");
      else if (a == 0x6A || a == 0x6B) Serial.print("  -> QMI8658/LSM6-class IMU (gyro)");
      Serial.println();
    }
  }
  Serial.printf("scan done: %d device(s)\n", found);
  delay(2000);
}
