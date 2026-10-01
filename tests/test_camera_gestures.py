import unittest

from remote_control.adapters.camera import GestureInterpreter, joint_angle, open_camera


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class FakeCapture:
    def __init__(self, opened):
        self.opened = opened
        self.released = False
        self.properties = []

    def isOpened(self):
        return self.opened

    def set(self, key, value):
        self.properties.append((key, value))

    def release(self):
        self.released = True


class FakeCv2:
    CAP_DSHOW = 1
    CAP_MSMF = 2
    CAP_ANY = 0
    CAP_PROP_FRAME_WIDTH = 3
    CAP_PROP_FRAME_HEIGHT = 4
    CAP_PROP_FPS = 5
    CAP_PROP_BUFFERSIZE = 6

    def __init__(self, successful_backend=None):
        self.successful_backend = successful_backend
        self.captures = []

    def VideoCapture(self, index, backend):
        capture = FakeCapture(backend == self.successful_backend)
        self.captures.append((index, backend, capture))
        return capture


class CameraGestureTests(unittest.TestCase):
    def test_swipe_right_and_cooldown(self):
        gestures = GestureInterpreter()
        self.assertIsNone(gestures.update_hand(0.2, 10.0))
        self.assertIsNone(gestures.update_hand(0.35, 10.2))
        self.assertEqual(gestures.update_hand(0.55, 10.4), "swipe_right")
        self.assertIsNone(gestures.update_hand(0.1, 10.5))

    def test_swipe_left(self):
        gestures = GestureInterpreter()
        gestures.update_hand(0.8, 20.0)
        gestures.update_hand(0.6, 20.2)
        self.assertEqual(gestures.update_hand(0.45, 20.4), "swipe_left")

    def test_only_seated_to_standing_triggers(self):
        gestures = GestureInterpreter()
        self.assertIsNone(gestures.update_pose([170, 170], 1.0))
        self.assertIsNone(gestures.update_pose([110, 120], 2.0))
        self.assertEqual(gestures.update_pose([165, 170], 4.1), "stand_up")
        self.assertIsNone(gestures.update_pose([170, 170], 4.5))

    def test_joint_angle(self):
        self.assertAlmostEqual(
            joint_angle(Point(0, 0), Point(0, 1), Point(0, 2)), 180.0
        )

    def test_camera_falls_back_from_directshow_to_media_foundation(self):
        cv2 = FakeCv2(successful_backend=FakeCv2.CAP_MSMF)
        capture, backend = open_camera(cv2, 2)
        self.assertEqual(backend, "Media Foundation")
        self.assertIs(capture, cv2.captures[1][2])
        self.assertTrue(cv2.captures[0][2].released)
        self.assertEqual(cv2.captures[0][0], 2)

    def test_camera_error_suggests_actionable_fixes(self):
        with self.assertRaisesRegex(RuntimeError, "another camera number"):
            open_camera(FakeCv2(), 0)
