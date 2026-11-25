#include <Servo.h>

// Protocol from controller/index.html: one "<channel> <angle>\n" per line at 9600 baud.
// The page already smooths motion and applies reverse/trim, so this just writes what it gets.

const int CHANNELS = 8;
const int PINS[CHANNELS] = {2, 3, 4, 5, 6, 7, 8, 9};

// Channel angles when every fader sits at 90 (DEFAULT_MAP in the page).
// 5 and 6 are the two shoulder servos, mirrored.
const int STRAIGHT[CHANNELS] = {90, 90, 87, 87, 90, 75, 105, 90};

Servo servos[CHANNELS];
char line[16];
int len = 0;

void setup() {
  Serial.begin(9600);
  for (int c = 0; c < CHANNELS; c++) {
    servos[c].write(STRAIGHT[c]);
    servos[c].attach(PINS[c]);
  }
  Serial.println("ready");
}

void handle(char *s) {
  char *rest;
  long c = strtol(s, &rest, 10);
  if (rest == s) return;
  char *end;
  long a = strtol(rest, &end, 10);
  if (end == rest || c < 0 || c >= CHANNELS || a < 0 || a > 180) {
    Serial.print("bad: ");
    Serial.println(s);
    return;
  }
  servos[c].write(a);
}

void loop() {
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\n' || ch == '\r') {
      line[len] = 0;
      if (len) handle(line);
      len = 0;
    } else if (len < (int)sizeof(line) - 1) {
      line[len++] = ch;
    }
  }
}
