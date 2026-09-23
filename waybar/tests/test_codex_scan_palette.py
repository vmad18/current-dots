"""Run: python3 -m unittest discover -s waybar/tests -v"""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codex_scan_palette import ScanPalette, transition

class PaletteTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
    def pick(self, colors):
        self.calls.append(tuple(colors))
        return colors[0]
    def update(self, state, watcher, active, now):
        return transition(state, watcher, active, now, self.pick)
    def active_pair(self, until):
        state, _ = self.update({}, "a", True, 0)
        for i in range(1, int(until * 2) + 1):
            state, _ = self.update(state, "a", True, i / 2)
            state, _ = self.update(state, "b", True, i / 2 + .01)
        return state
    def test_inactive_and_shared_activation(self):
        state, color = self.update({}, "a", False, 0)
        self.assertIsNone(color)
        self.assertEqual(self.calls, [])
        state, first = self.update(state, "a", True, .1)
        state, second = self.update(state, "b", True, .2)
        self.assertEqual(first, second)
        self.assertEqual(len(self.calls), 1)
    def test_one_switch_at_30_seconds(self):
        state = self.active_pair(29.5)
        self.assertEqual(len(self.calls), 1)
        state, first = self.update(state, "a", True, 30)
        state, second = self.update(state, "b", True, 30.01)
        self.assertEqual(first, "blue")
        self.assertEqual(first, second)
        self.assertEqual(len(self.calls), 2)
        self.assertNotIn("orange", self.calls[-1])
        self.assertEqual(state["changed_at"], 30)
    def test_switch_repeats_at_60_seconds(self):
        state = self.active_pair(60)
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(state["color"], "orange")
        self.assertNotIn("blue", self.calls[-1])
    def test_only_all_inactive_resets_timer(self):
        state = self.active_pair(1)
        state, color = self.update(state, "a", False, 1.2)
        self.assertIsNone(color)
        self.assertEqual(state["changed_at"], 0)
        state, _ = self.update(state, "b", False, 1.3)
        self.assertIsNone(state["changed_at"])
        old = copy.deepcopy(state)
        state, _ = self.update(state, "a", True, 1.4)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(state["changed_at"], 1.4)
        self.assertFalse(old["watchers"]["a"]["working"])
    def test_expired_watchers_do_not_hold_old_activity(self):
        state, _ = self.update({}, "a", True, 0)
        state, _ = self.update(state, "b", True, 4)
        self.assertEqual(list(state["watchers"]), ["b"])
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(state["changed_at"], 4)
    def test_legacy_or_invalid_time_keeps_current_color(self):
        for stamp in (None, float("nan"), 200):
            state = {"color": "purple", "changed_at": stamp,
                     "watchers": {"a": {"working": True, "seen_at": 100}}}
            state, color = self.update(state, "a", True, 100.1)
            self.assertEqual(color, "purple")
            self.assertEqual(state["changed_at"], 100.1)
        self.assertEqual(self.calls, [])
    def test_malformed_state(self):
        for state in (None, {"watchers": []}, {"watchers": {"old": "bad"}}):
            state, color = self.update(state, "a", True, 1)
            self.assertEqual(color, "orange")
    def test_persistent_wrapper_keeps_watchers_synchronized(self):
        import threading
        store = {}
        lock = threading.Lock()
        def load(path, default):
            return copy.deepcopy(store.get(path, default))
        def write(path, value):
            store[path] = copy.deepcopy(value)
        one = ScanPalette("palette", lambda: lock, load, write)
        two = ScanPalette("palette", lambda: lock, load, write)
        with patch("codex_scan_palette.time.monotonic", return_value=0):
            first = one.color_for(True)
            self.assertEqual(two.color_for(True), first)
        for second in range(1, 31):
            with patch("codex_scan_palette.time.monotonic", return_value=second):
                a, b = one.color_for(True), two.color_for(True)
                self.assertEqual(a, b)
                if second < 30:
                    self.assertEqual(a, first)
        self.assertNotEqual(a, first)

if __name__ == "__main__":
    unittest.main()
