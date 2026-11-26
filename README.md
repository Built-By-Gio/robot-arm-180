# 180° - 6-DOF robot arm with camera calibration

A 6-DOF servo arm with a gripper, built from fabricreator's arm design on Cults3D and driven by an Arduino Uno. This repository holds the control side: the Arduino sketch that drives the eight servos over serial, and a camera calibration script. The script uses OpenCV to find a coloured marker on the gripper while the arm steps through joint angles, fits a least-squares model from joint angles to camera pixels, and then lets you click a point in the camera view so the arm moves there. A browser controller called **180°** (three.js 3D view, Web Serial, pose sequencer) was also built for this arm; it is not in this repository yet (see Status).

Built by Gio ([Built-By-Gio](https://github.com/Built-By-Gio)).

## Status (2026-11-25)

**Built and working**
- The arm is printed, assembled and wired to an Arduino Uno, with all joints moving. Photos and a clip of the 180° controller page driving the real arm are not in this repository yet.
- Camera calibration and click-to-move worked on the real arm on 2026-10-20.

**Rewritten in November 2026**
- The original Arduino sketch and the original calibration script are on another computer. `firmware/arm_serial/arm_serial.ino` and `training/train.py` in this repository were rewritten to match the controller's serial protocol and channel map, and they run on the real arm.

**Not in this repository yet**
- The 180° browser controller (`controller/index.html`). Its 3D view embeds arm meshes exported from a Blender model of the arm, and I have not checked the license of fabricreator's design yet, so I am holding the file back until that is settled.
- The printable arm files. They belong to fabricreator and must be obtained from the designer on Cults3D.

**Still to add**
- Servo models, power supply rating and print settings.
- The exact Cults3D page and license of the arm design.

## What you need

- The printed arm from fabricreator's design on Cults3D (get the files from the designer).
- 8 hobby servos on 7 joints (the shoulder uses two servos, mirrored).
- Arduino Uno and a USB cable.
- A separate 5-6 V supply for the servos. Do not power them from the Uno's 5 V pin; tie the grounds together.
- A webcam and a pink marker (tape) on the gripper, for calibration.
- Arduino IDE (the Servo library ships with it).
- Python 3 (I use 3.13) and the packages `opencv-python`, `numpy` and `pyserial`.

### Wiring

| Channel | Uno pin | Joint | Angle at "straight" |
|---|---|---|---|
| 0 | 2 | Gripper | 90 |
| 1 | 3 | Wrist | 90 |
| 2 | 4 | Forearm 2 | 87 |
| 3 | 5 | Forearm | 87 |
| 4 | 6 | Elbow | 90 |
| 5 | 7 | Shoulder A | 75 |
| 6 | 8 | Shoulder B (mirrored) | 105 |
| 7 | 9 | Base | 90 |

The serial protocol is one `<channel> <angle>` line per command at 9600 baud, for example `7 90`.

## How to build / run

1. Print and assemble the arm following fabricreator's instructions.
2. Wire the servo signal leads to pins 2-9 as in the table, and power the servos from their own 5-6 V supply with a common ground.
3. Open `firmware/arm_serial/arm_serial.ino` in the Arduino IDE, select **Arduino Uno** and the right port, and upload. On boot every servo goes to its "straight" angle and the board prints `ready`.
4. Install the Python packages: `pip install opencv-python numpy pyserial`.
5. Point the webcam at the arm and put the pink marker on the gripper.
6. In `training/`, collect samples (replace `COM5` with your port; only one program can hold the port at a time):
   `python train.py collect --port COM5`
   The arm steps through 378 base/shoulder/elbow poses and writes `samples.csv`. If the marker is not found, add `--show` to see the colour mask and adjust `MARKER_LOW` / `MARKER_HIGH` in the script.
7. Fit the model: `python train.py fit`. It prints the mean and worst error in pixels and saves `model.json`.
8. Click to move: `python train.py click --port COM5`, then click a point in the camera window. The script searches the fitted model for the pose that lands on that pixel, preferring the one closest to the current pose. Press Esc to quit; the arm returns home.

## Repo layout

| Path | Contents |
|---|---|
| `firmware/arm_serial/arm_serial.ino` | Arduino sketch: reads `<channel> <angle>` lines and writes them to 8 servos |
| `training/train.py` | Camera calibration: collect, fit, click |

## Roadmap / future plans

- Self-modeling: have the arm learn its own body (link lengths) from the camera instead of entering them by hand.

## Timeline

- August 2026: build started.
- 2026-10-20: calibration working, click-to-move on the real arm.

## Credits and license

- Mechanical arm design: **fabricreator** on Cults3D. The printable files are not included here; obtain them from the designer and follow the designer's license.
- Uses OpenCV, NumPy, pyserial and the Arduino Servo library (installed separately, not included).
- The 180° controller uses three.js r128 (MIT) and anime.js, loaded from a CDN.

The code in this repository is released under the MIT License (see `LICENSE`). The license does not cover fabricreator's design.
