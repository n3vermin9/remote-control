from __future__ import annotations

import math
import threading
import time
from collections import deque
from pathlib import Path
from typing import Callable, Deque, Optional, Sequence, Tuple


GestureHandler = Callable[[str], None]
StatusHandler = Callable[[str], None]
FrameHandler = Callable[[object], None]


def joint_angle(a, b, c) -> float:  # noqa: ANN001
    """Return the angle ABC in degrees for normalized landmark objects."""
    first = math.atan2(c.y - b.y, c.x - b.x)
    second = math.atan2(a.y - b.y, a.x - b.x)
    return abs(math.degrees((first - second + math.pi) % (2 * math.pi) - math.pi))


class GestureInterpreter:
    """Debounces landmark movement into deliberate media gestures."""

    def __init__(self) -> None:
        self.hand_history: Deque[Tuple[float, float]] = deque()
        self.last_swipe_at = 0.0
        self.pose_state: Optional[str] = None
        self.last_stand_at = 0.0

    def update_hand(self, x: float, now: float) -> Optional[str]:
        while self.hand_history and now - self.hand_history[0][0] > 0.7:
            self.hand_history.popleft()
        self.hand_history.append((now, x))
        if now - self.last_swipe_at < 1.2 or len(self.hand_history) < 3:
            return None
        elapsed = now - self.hand_history[0][0]
        movement = x - self.hand_history[0][1]
        if elapsed < 0.12 or abs(movement) < 0.28:
            return None
        self.last_swipe_at = now
        self.hand_history.clear()
        return "swipe_right" if movement > 0 else "swipe_left"

    def update_pose(self, knee_angles: Sequence[float], now: float) -> Optional[str]:
        if not knee_angles:
            return None
        average = sum(knee_angles) / len(knee_angles)
        if average <= 135:
            self.pose_state = "seated"
            return None
        if average >= 158:
            previous = self.pose_state
            self.pose_state = "standing"
            if previous == "seated" and now - self.last_stand_at >= 2.0:
                self.last_stand_at = now
                return "stand_up"
        return None


class CameraGestureAdapter:
    def __init__(
        self,
        hand_model_path: Path,
        pose_model_path: Path,
        camera_index: int = 0,
        status: StatusHandler = print,
    ) -> None:
        self.hand_model_path = hand_model_path
        self.pose_model_path = pose_model_path
        self.camera_index = camera_index
        self.status = status
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(
        self,
        on_gesture: GestureHandler,
        on_frame: Optional[FrameHandler] = None,
    ) -> None:
        if not self.hand_model_path.exists() or not self.pose_model_path.exists():
            raise FileNotFoundError("Webcam gesture models are missing. Run INSTALL.bat again.")

        import cv2
        import mediapipe as mp

        vision = mp.tasks.vision
        base_options = mp.tasks.BaseOptions
        hand_options = vision.HandLandmarkerOptions(
            base_options=base_options(model_asset_path=str(self.hand_model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.6,
            min_hand_presence_confidence=0.6,
            min_tracking_confidence=0.6,
        )
        pose_options = vision.PoseLandmarkerOptions(
            base_options=base_options(model_asset_path=str(self.pose_model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.6,
            min_pose_presence_confidence=0.6,
            min_tracking_confidence=0.6,
        )

        backend = cv2.CAP_DSHOW if hasattr(cv2, "CAP_DSHOW") else 0
        capture = cv2.VideoCapture(self.camera_index, backend)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        capture.set(cv2.CAP_PROP_FPS, 15)
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f"Could not open camera {self.camera_index}.")

        interpreter = GestureInterpreter()
        last_timestamp = 0
        self.status("Webcam gestures active: stand up, or swipe a hand left/right.")
        try:
            with vision.HandLandmarker.create_from_options(hand_options) as hands, \
                    vision.PoseLandmarker.create_from_options(pose_options) as poses:
                while not self._stop_event.is_set():
                    ok, frame = capture.read()
                    if not ok:
                        self.status("Camera frame could not be read.")
                        break
                    frame = cv2.flip(frame, 1)
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                    timestamp = max(last_timestamp + 1, int(time.monotonic() * 1000))
                    last_timestamp = timestamp

                    hand_result = hands.detect_for_video(image, timestamp)
                    if hand_result.hand_landmarks:
                        wrist = hand_result.hand_landmarks[0][0]
                        gesture = interpreter.update_hand(wrist.x, time.monotonic())
                        if gesture:
                            on_gesture(gesture)

                    pose_result = poses.detect_for_video(image, timestamp)
                    if pose_result.pose_landmarks:
                        landmarks = pose_result.pose_landmarks[0]
                        angles = []
                        for hip, knee, ankle in ((23, 25, 27), (24, 26, 28)):
                            points = (landmarks[hip], landmarks[knee], landmarks[ankle])
                            if all((point.visibility or 0) >= 0.45 for point in points):
                                angles.append(joint_angle(*points))
                        gesture = interpreter.update_pose(angles, time.monotonic())
                        if gesture:
                            on_gesture(gesture)

                    if on_frame:
                        on_frame(rgb)
        finally:
            capture.release()
            self.status("Webcam gestures stopped.")
