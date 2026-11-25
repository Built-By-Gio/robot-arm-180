"""Camera training for the 180° arm.

collect  jog the arm through a grid of base/shoulder/elbow angles, find the
         colored marker on the gripper in each frame, log it to samples.csv
fit      fit joint angles -> camera pixel and save model.json
click    show the camera, click a spot, and the arm moves there

  python train.py collect --port COM5
  python train.py fit
  python train.py click --port COM5
"""

import argparse
import csv
import itertools
import json
import time

import cv2
import numpy as np
import serial

# Same as DEFAULT_MAP in controller/index.html: channel -> (joint, reversed, trim).
CHANNEL_MAP = [(6, True, 0), (5, True, 0), (4, True, -3), (3, True, -3),
               (2, True, 0), (1, True, -15), (1, False, 15), (0, True, 0)]
HOME = [90, 120, 150, 90, 90, 90, 170]

# Pink tape on the gripper. Tune with --show if the mask misses it.
MARKER_LOW = np.array([145, 90, 90])
MARKER_HIGH = np.array([175, 255, 255])

BASE = range(50, 131, 10)
SHOULDER = range(100, 151, 10)
ELBOW = range(110, 171, 10)


def to_channels(joints):
    out = []
    for joint, rev, trim in CHANNEL_MAP:
        v = 180 - joints[joint] if rev else joints[joint]
        out.append(max(0, min(180, round(v + trim))))
    return out


class Arm:
    def __init__(self, port):
        self.ser = serial.Serial(port, 9600, timeout=1)
        time.sleep(2)  # the Uno resets when the port opens
        self.joints = list(HOME)
        self.send()

    def send(self):
        lines = "".join(f"{c} {v}\n" for c, v in enumerate(to_channels(self.joints)))
        self.ser.write(lines.encode())

    # Steps in 2° increments so it never snaps across the range.
    def move(self, target, step=2, pause=0.02):
        while self.joints != target:
            self.joints = [j + max(-step, min(step, t - j)) for j, t in zip(self.joints, target)]
            self.send()
            time.sleep(pause)


def find_marker(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, MARKER_LOW, MARKER_HIGH)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, mask
    c = max(contours, key=cv2.contourArea)
    if cv2.contourArea(c) < 40:
        return None, mask
    m = cv2.moments(c)
    return (m["m10"] / m["m00"], m["m01"] / m["m00"]), mask


def grab(cam, n=5):
    for _ in range(n):  # flush stale frames from the driver buffer
        ok, frame = cam.read()
    return frame if ok else None


def collect(args):
    arm = Arm(args.port)
    cam = cv2.VideoCapture(args.camera)
    grid = list(itertools.product(BASE, SHOULDER, ELBOW))
    found = 0
    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["base", "shoulder", "elbow", "px", "py"])
        for i, (b, s, e) in enumerate(grid):
            arm.move([b, s, e, 90, 90, 90, 170])
            time.sleep(args.settle)
            frame = grab(cam)
            if frame is None:
                continue
            pt, mask = find_marker(frame)
            if pt:
                w.writerow([b, s, e, round(pt[0], 1), round(pt[1], 1)])
                found += 1
                cv2.circle(frame, (int(pt[0]), int(pt[1])), 8, (0, 255, 0), 2)
            cv2.putText(frame, f"{i + 1}/{len(grid)}  found {found}", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.imshow("collect", mask if args.show else frame)
            if cv2.waitKey(1) == 27:
                break
    arm.move(list(HOME))
    print(f"{found} of {len(grid)} poses saw the marker -> {args.out}")


def features(angles):
    a = (np.asarray(angles, dtype=float) - 90) / 90
    cols = [np.ones(len(a))]
    for i in range(3):
        cols.append(a[:, i])
        for j in range(i, 3):
            cols.append(a[:, i] * a[:, j])
    return np.column_stack(cols)


# Fits angles -> pixel. Going the other way isn't a function: lots of shoulder/elbow
# pairs land on the same pixel, so click() searches this model instead.
def fit(args):
    data = np.loadtxt(args.data, delimiter=",", skiprows=1)
    angles, pixels = data[:, :3], data[:, 3:5]
    X = features(angles)
    coef, *_ = np.linalg.lstsq(X, pixels, rcond=None)
    err = np.linalg.norm(X @ coef - pixels, axis=1)
    print(f"{len(data)} samples, mean error {err.mean():.1f} px, worst {err.max():.1f} px")
    json.dump({"coef": coef.tolist()}, open(args.model, "w"))
    print(f"saved {args.model}")


def solve(coef, x, y, current):
    grid = np.array(list(itertools.product(range(BASE.start, BASE.stop, 2),
                                           range(SHOULDER.start, SHOULDER.stop, 2),
                                           range(ELBOW.start, ELBOW.stop, 2))))
    miss = np.linalg.norm(features(grid) @ coef - [x, y], axis=1)
    travel = np.abs(grid - current[:3]).sum(axis=1)
    return grid[np.argmin(miss + 0.05 * travel)], miss.min()


def click(args):
    coef = np.array(json.load(open(args.model))["coef"])
    arm = Arm(args.port)
    cam = cv2.VideoCapture(args.camera)
    target = []

    def on_mouse(event, x, y, *_):
        if event == cv2.EVENT_LBUTTONDOWN:
            (b, s, e), miss = solve(coef, x, y, arm.joints)
            target[:] = [x, y]
            print(f"click {x},{y} -> base {b} shoulder {s} elbow {e} ({miss:.0f} px off)")
            arm.move([int(b), int(s), int(e), 90, 90, 90, arm.joints[6]])

    cv2.namedWindow("click")
    cv2.setMouseCallback("click", on_mouse)
    while True:
        ok, frame = cam.read()
        if not ok:
            break
        pt, _ = find_marker(frame)
        if pt:
            cv2.circle(frame, (int(pt[0]), int(pt[1])), 8, (0, 255, 0), 2)
        if target:
            cv2.drawMarker(frame, tuple(target), (0, 0, 255), cv2.MARKER_CROSS, 20, 2)
        cv2.imshow("click", frame)
        if cv2.waitKey(1) == 27:
            break
    arm.move(list(HOME))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--port", required=True)
    c.add_argument("--camera", type=int, default=0)
    c.add_argument("--settle", type=float, default=0.6)
    c.add_argument("--out", default="samples.csv")
    c.add_argument("--show", action="store_true", help="show the marker mask instead of the camera")
    f = sub.add_parser("fit")
    f.add_argument("--data", default="samples.csv")
    f.add_argument("--model", default="model.json")
    k = sub.add_parser("click")
    k.add_argument("--port", required=True)
    k.add_argument("--camera", type=int, default=0)
    k.add_argument("--model", default="model.json")
    args = p.parse_args()
    {"collect": collect, "fit": fit, "click": click}[args.cmd](args)


if __name__ == "__main__":
    main()
