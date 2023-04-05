from pyggp.interpreters import State
from pyggp.visualizers import SimpleVisualizer


def test_update_abort() -> None:
    visualizer = SimpleVisualizer()

    assert visualizer._aborted is False

    visualizer.update_abort()

    assert visualizer._aborted is True


def test_draw() -> None:
    visualizer = SimpleVisualizer()

    states = [State(frozenset()), None, State(frozenset())]
    visualizer._states = states

    assert visualizer._last_drawn_ply == -1

    visualizer.draw()

    assert visualizer._last_drawn_ply == 2
