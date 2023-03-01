# pylint: disable=missing-docstring,invalid-name,unused-argument
from time import sleep
from unittest import TestCase

from pyggp.gameclocks import GameClockConfiguration, GameClock


class TestGameClock(TestCase):
    def test_game_clock_delay(self) -> None:
        game_clock_config = GameClockConfiguration(total_time=0.0, increment=0.0, delay=0.1)

        game_clock = GameClock(game_clock_config)
        with game_clock:
            sleep(0.2)
        self.assertTrue(game_clock.is_expired)

    def test_game_clock_increment(self) -> None:
        game_clock_config = GameClockConfiguration(total_time=0.0, increment=10.0, delay=10.0)

        game_clock = GameClock(game_clock_config)
        with game_clock:
            pass
        self.assertGreaterEqual(game_clock.total_time_ns, 0)
        self.assertLessEqual(game_clock.total_time_ns, 10_000_000_000)

    def test_game_clock_repr_zero(self) -> None:
        game_clock_config = GameClockConfiguration(total_time=0.0, increment=0.0, delay=0.0)

        game_clock = GameClock(game_clock_config)
        actual = repr(game_clock)
        expected = "0. | 0 d0"
        self.assertEqual(actual, expected)

    def test_game_clock_repr_expired(self) -> None:
        game_clock_config = GameClockConfiguration(total_time=-0.5, increment=0.0, delay=0.0)

        game_clock = GameClock(game_clock_config)
        actual = repr(game_clock)
        expected = "0 | 0 d0"
        self.assertEqual(actual, expected)

    def test_game_clock_repr_increment_decimal(self) -> None:
        game_clock_config = GameClockConfiguration(total_time=0.0, increment=0.1, delay=0.0)

        game_clock = GameClock(game_clock_config)
        actual = repr(game_clock)
        expected = "0. | 0.1 d0"
        self.assertEqual(actual, expected)

    def test_game_clock_repr_increment_integer(self) -> None:
        game_clock_config = GameClockConfiguration(total_time=0.0, increment=1.0, delay=0.0)

        game_clock = GameClock(game_clock_config)
        actual = repr(game_clock)
        expected = "0. | 1 d0"
        self.assertEqual(actual, expected)

    def test_game_clock_repr_delay_decimal(self) -> None:
        game_clock_config = GameClockConfiguration(total_time=0.0, increment=0.0, delay=0.1)

        game_clock = GameClock(game_clock_config)
        actual = repr(game_clock)
        expected = "0. | 0 d0.1"
        self.assertEqual(actual, expected)

    def test_game_clock_repr_delay_integer(self) -> None:
        game_clock_config = GameClockConfiguration(total_time=0.0, increment=0.0, delay=1.0)

        game_clock = GameClock(game_clock_config)
        actual = repr(game_clock)
        expected = "0. | 0 d1"
        self.assertEqual(actual, expected)

    def test_game_clock_repr_total_time_milliseconds(self) -> None:
        game_clock_config = GameClockConfiguration(total_time=0.001, increment=0.0, delay=0.0)

        game_clock = GameClock(game_clock_config)
        actual = repr(game_clock)
        expected = "0.0010 | 0 d0"
        self.assertEqual(actual, expected)

    def test_game_clock_repr_total_time_centiseconds(self) -> None:
        game_clock_config = GameClockConfiguration(total_time=0.2, increment=0.0, delay=0.0)

        game_clock = GameClock(game_clock_config)
        actual = repr(game_clock)
        expected = "0.200 | 0 d0"
        self.assertEqual(actual, expected)

    def test_game_clock_repr_total_time_seconds(self) -> None:
        game_clock_config = GameClockConfiguration(total_time=2.0, increment=0.0, delay=0.0)

        game_clock = GameClock(game_clock_config)
        actual = repr(game_clock)
        expected = "2.00 | 0 d0"
        self.assertEqual(actual, expected)

    def test_game_clock_repr_total_time_halfminute(self) -> None:
        game_clock_config = GameClockConfiguration(total_time=32.0, increment=0.0, delay=0.0)

        game_clock = GameClock(game_clock_config)
        actual = repr(game_clock)
        expected = "32.0 | 0 d0"
        self.assertEqual(actual, expected)

    def test_game_clock_repr_total_time_minute(self) -> None:
        game_clock_config = GameClockConfiguration(total_time=100.0, increment=0.0, delay=0.0)

        game_clock = GameClock(game_clock_config)
        actual = repr(game_clock)
        expected = "1:40 | 0 d0"
        self.assertEqual(actual, expected)

    def test_game_clock_get_timeout(self) -> None:
        game_clock_config = GameClockConfiguration(total_time=0.0, increment=0.0, delay=0.0)

        game_clock = GameClock(game_clock_config)
        actual = game_clock.get_timeout(0.0)
        expected = 0.0
        self.assertEqual(actual, expected)
