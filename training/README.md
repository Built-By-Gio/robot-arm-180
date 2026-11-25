`train.py` has three steps:

1. **collect**: steps the arm through 378 base/shoulder/elbow poses, finds the pink marker on the gripper in each frame, and writes `samples.csv`.
2. **fit**: fits joint angles → camera pixel and saves `model.json`. It prints the average miss in pixels.
3. **click**: shows the camera. Click a spot and it searches the model for the pose that lands there, preferring the one closest to where the arm already is.

If the marker isn't found, run `collect --show` to see the mask and adjust `MARKER_LOW` / `MARKER_HIGH`.
