"""Headless checks for UI navigation, modal input and readable long content."""
import os
import unittest
import warnings
from unittest.mock import patch

import pygame

from game import Game
from ui import W, H


class TestGameUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.environment = patch.dict(os.environ, {"SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"})
        cls.environment.start()
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="no fast renderer available")
            cls.game = Game()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()
        cls.environment.stop()

    def setUp(self):
        self.g = self.game
        self.g.reset()
        self.g.state = "menu"
        self.g.running = True
        self.g.draw()

    def press(self, key):
        self.g.handle(pygame.event.Event(pygame.KEYDOWN, key=key))
        self.g.draw()

    def click(self, action):
        rect = next(rect for rect, key in self.g.ui_buttons if key == action)
        self.g.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))
        self.g.draw()

    def collect(self):
        for b in self.g.k.bukti:
            self.g.add_bukti(b)
        self.g.aria_shown = len(self.g.aria_text)

    def test_mouse_investigation_to_result_and_replay(self):
        self.click(pygame.K_RETURN)
        self.assertEqual(self.g.state, "play")
        self.collect()
        self.g.draw()
        self.click(pygame.K_j)
        self.click(("journal", 8))
        self.assertEqual(self.g.sel, 8)
        self.click(pygame.K_j)
        self.click(pygame.K_k)
        self.click(pygame.K_2)
        for i, b in enumerate(self.g.k.bukti):
            if b.relevan:
                self.click(("evidence", i))
        self.click(pygame.K_RETURN)
        self.assertEqual(self.g.state, "result")
        self.assertTrue(self.g.result["benar"])
        self.assertEqual(self.g.result["total"], 100)
        self.click(pygame.K_r)
        self.assertEqual(self.g.state, "play")
        self.assertEqual(self.g.found, [])

    def test_modals_only_register_their_own_controls(self):
        self.press(pygame.K_RETURN)
        self.press(pygame.K_j)
        self.assertNotIn(pygame.K_h, [key for _, key in self.g.ui_buttons])
        self.assertNotIn(pygame.K_k, [key for _, key in self.g.ui_buttons])
        self.press(pygame.K_ESCAPE)
        self.press(pygame.K_k)
        self.assertNotIn(pygame.K_RETURN, [key for _, key in self.g.ui_buttons])
        self.press(pygame.K_1)
        self.assertIn(pygame.K_RETURN, [key for _, key in self.g.ui_buttons])

    def test_aria_and_journal_scroll_reach_end_and_clamp(self):
        self.press(pygame.K_RETURN)
        self.g.aria_say("Penjelasan bukti dan probabilitas tersangka. " * 30)
        self.g.aria_shown = len(self.g.aria_text)
        self.g.draw()
        self.assertGreater(self.g.aria_scroll_max, 0)
        with patch("pygame.mouse.get_pos", return_value=self.g.aria_scroll_rect.center):
            self.g.handle(pygame.event.Event(pygame.MOUSEWHEEL, y=-1000))
            self.assertEqual(self.g.aria_scroll, self.g.aria_scroll_max)
            self.g.handle(pygame.event.Event(pygame.MOUSEWHEEL, y=1000))
            self.assertEqual(self.g.aria_scroll, 0)
        self.press(pygame.K_PAGEDOWN)
        self.assertGreater(self.g.aria_scroll, 0)
        self.collect()
        self.press(pygame.K_j)
        self.assertGreater(self.g.journal_scroll_max, 0)
        with patch("pygame.mouse.get_pos", return_value=self.g.ui_scroll_rect.center):
            self.g.handle(pygame.event.Event(pygame.MOUSEWHEEL, y=-1000))
            self.assertEqual(self.g.journal_scroll, self.g.journal_scroll_max)
        self.click(("journal", 1))
        self.assertEqual(self.g.journal_scroll, 0)
        self.press(pygame.K_PAGEDOWN)
        self.assertGreater(self.g.journal_scroll, 0)
        self.press(pygame.K_DOWN)
        self.assertEqual(self.g.journal_scroll, 0)

    def test_dialog_can_be_read_and_closed_with_mouse(self):
        self.press(pygame.K_RETURN)
        self.g.px, self.g.py = 150, 95
        self.press(pygame.K_e)
        self.assertIn("E1", self.g.found)
        self.assertIsNotNone(self.g.dialog)
        self.assertEqual([key for _, key in self.g.ui_buttons], [pygame.K_e])
        self.click(pygame.K_e)
        self.assertEqual(self.g.dialog["shown"], len(self.g.dialog["text"]))
        self.click(pygame.K_e)
        self.assertIsNone(self.g.dialog)
        self.assertEqual(self.g.found.count("E1"), 1)

    def test_screens_and_controls_stay_in_view(self):
        self.press(pygame.K_RETURN)
        self.collect()
        for state in ("play", "journal", "accuse"):
            self.g.state = state
            self.g.draw()
            self.assertEqual(self.g.screen.get_size(), (W, H))
            for rect, _ in self.g.ui_buttons:
                self.assertTrue(self.g.screen.get_rect().contains(rect), (state, rect))
        for suspect in self.g.k.tersangka:
            self.g.acc_suspect = suspect.id
            self.g.submit()
            self.g.draw()
            self.assertEqual(self.g.state, "result")


if __name__ == "__main__":
    unittest.main()
