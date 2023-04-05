from unittest import mock

from pyggp.visualizers import Visualizer


@mock.patch.object(Visualizer, "__abstractmethods__", set())
def test_update_state_no_ply() -> None:
    visualizer = Visualizer()

    states = mock.MagicMock()
    visualizer._states = states

    state = mock.MagicMock()

    visualizer.update_state(state)

    states.append.assert_called_once_with(state)


@mock.patch.object(Visualizer, "__abstractmethods__", set())
def test_update_state_next_ply() -> None:
    visualizer = Visualizer()

    states = mock.MagicMock()
    visualizer._states = states

    state = mock.MagicMock()

    visualizer.update_state(state, ply=0)

    states.extend.assert_called_once_with([None])
    states.__setitem__.assert_called_once_with(0, state)


@mock.patch.object(Visualizer, "__abstractmethods__", set())
def test_update_state_future_ply() -> None:
    visualizer = Visualizer()

    states = mock.MagicMock()
    visualizer._states = states

    state = mock.MagicMock()

    visualizer.update_state(state, ply=2)

    states.extend.assert_called_once_with([None, None, None])
    states.__setitem__.assert_called_once_with(2, state)
