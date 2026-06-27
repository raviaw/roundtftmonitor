# Round ESP32 display — hardware identification

_Identified 2026-06-26 by reading the chip and flash directly (esptool v5.3.0)._

## What it is
A **GUITION ESP32-C3 round touch LCD board** (1.28" 240×240 round IPS class,
GC9A01-style panel + capacitive touch — touch confirmed by user). Shipped running
GUITION's factory **LVGL "Smart Watch" demo**.

## Chip (read off silicon)
- **ESP32-C3** (QFN32), revision **v0.4**
- Single-core 32-bit **RISC-V @ 160 MHz**
- **Wi-Fi** + **Bluetooth 5 (LE)**
- **4 MB** embedded flash (XMC, manuf 0x46 / dev 0x4016)
- 40 MHz crystal
- Native **USB-Serial/JTAG** (USB is built into the C3 — no CH340/CP210x bridge)
- **MAC 10:b4:1d:20:45:88** (OUI 10:b4:1d = Espressif)

## How it shows up on Windows
- VID `303A` / PID `1001` (Espressif native USB)
- **COM5** = "USB Serial Device" (the CDC port — use this to flash/talk)
- Also a "USB JTAG/serial debug unit" interface (MI_02)
- Composite device serial = the MAC above

## Firmware currently on it
- Built with **Arduino-ESP32 core**, ESP-IDF **v4.4.3**, compiled **Dec 20 2022**
- App-descriptor magic 0xABCD5432 OK; project_name `arduino-lib-builder` (stock Arduino)
- **LVGL** UI — flash contains the stock `I am LVGL_Arduino` banner
- GUITION branding strings: `by GUITION`, `GUITION`, `Powered By`
- Demo screens: Smart Watch face, Lap info, Navigation/Turn Right, Hour forecast,
  Wi-Fi Setting (`Input SSID and password`) — a Wi-Fi-connected smartwatch demo
- Includes ESP HTTP client + httpd (the Wi-Fi config portal)

## Partition table (read from 0x8000)
| label    | type | subtype | offset    | size    |
|----------|------|---------|-----------|---------|
| nvs      | data | 0x02    | 0x09000   | 20 KB   |
| otadata  | data | 0x00    | 0x0E000   | 8 KB    |
| app0     | app  | 0x10    | 0x10000   | 3072 KB |
| spiffs   | data | 0x82    | 0x310000  | 896 KB  |
| coredump | data | 0x03    | 0x3F0000  | 64 KB   |

Single-app layout (no OTA app1). 3 MB available for a replacement sketch.

## Model + pinout (confirmed via board docs; verified empirically by probe)
Board is the **GUITION ESP32-2424S012**:
- LCD driver: **GC9A01** (1.28" round 240×240 IPS)
- Touch: **CST816D**, I2C address **0x15**
- No IMU populated

| Function | GPIO | | Function | GPIO |
|---|---|---|---|---|
| LCD SCLK | 6 | | Touch SDA (I2C) | 4 |
| LCD MOSI | 7 | | Touch SCL (I2C) | 5 |
| LCD DC | 2 | | Touch INT | 0 |
| LCD CS | 10 | | Touch RST | 1 |
| LCD BL | 3 | | BOOT button | 9 |
| LCD RST | none (chip reset) | | **GPIO 8** | free |

USB on GPIO 18/19, UART0 on GPIO 20/21. Only **GPIO 8** is spare.

## Notes
- Nothing was erased during identification — esptool only **read** flash + reset.
- To flash: `esptool --port COM5 ...` works directly (native USB, no button combo
  usually needed; hold BOOT + tap RST if it won't connect).
