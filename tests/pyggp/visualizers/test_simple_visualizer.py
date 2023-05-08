from pyggp.engine_primitives import State
from pyggp.visualizers import SimpleVisualizer


def test_update_abort() -> None:
    visualizer = SimpleVisualizer()

    assert visualizer.aborted is False

    visualizer.update_abort()

    assert visualizer.aborted is True


def test_draw() -> None:
    visualizer = SimpleVisualizer()

    states = [State(frozenset()), None, State(frozenset())]
    visualizer.states = states

    assert visualizer.last_drawn_ply == -1

    visualizer.draw()

    assert visualizer.last_drawn_ply == 2
