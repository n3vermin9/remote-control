import unittest

from remote_control.adapters.camera import GestureInterpreter, joint_angle


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y


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
