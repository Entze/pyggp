import pytest
from pyggp.agents.tree_agents.nodes import Node


@pytest.mark.parametrize(
    ("node", "expected"),
    [
        (Node(), 0),
        (Node(parent=Node()), 1),
        (Node(parent=Node(parent=Node())), 2),
        (Node(children={frozenset(): Node()}), 0),
        (Node(parent=Node(), children={frozenset(): Node()}), 1),
    ],
)
def test_depth(node: Node, expected: int) -> None:
    actual = node.depth
    assert actual == expected


@pytest.mark.parametrize(
    ("node", "expected"),
    [
        (Node(), 0),
        (Node(parent=Node()), 0),
        (Node(parent=Node(parent=Node())), 0),
        (Node(children={frozenset(): Node()}), 1),
        (Node(parent=Node(), children={frozenset(): Node()}), 1),
    ],
)
def test_height(node: Node, expected: int) -> None:
    actual = node.height
    assert actual == expected


def test_trim_two_children() -> None:
    parent = Node()
    child1 = Node(parent=parent)
    child2 = Node(parent=parent)
    children = {frozenset({(0, 0)}): child1, frozenset({(0, 1)}): child2}
    parent.children = children
    parent.role_move_mapping = {0: 0}
    assert len(parent.children) == 2
    assert parent.children == children
    parent.trim()
    assert len(parent.children) == 1
    assert parent.children == {frozenset({(0, 0)}): child1}


def test_trim_is_idempotent() -> None:
    parent = Node()
    child1 = Node(parent=parent)
    child2 = Node(parent=parent)
    children = {frozenset({(0, 0)}): child1, frozenset({(0, 1)}): child2}
    parent.children = children
    parent.role_move_mapping = {0: 0}
    assert len(parent.children) == 2
    assert parent.children == children
    parent.trim()
    assert len(parent.children) == 1
    assert parent.children == {frozenset({(0, 0)}): child1}
    parent.trim()
    assert len(parent.children) == 1
    assert parent.children == {frozenset({(0, 0)}): child1}


def test_trim_no_children_nothing_happens() -> None:
    parent = Node()
    assert parent.children is None
    parent.trim()
    assert parent.children is None


def test_trim_no_move_nothing_happens() -> None:
    parent = Node()
    child1 = Node(parent=parent)
    child2 = Node(parent=parent)
    children = {frozenset({(0, 0)}): child1, frozenset({(0, 1)}): child2}
    parent.children = children
    assert len(parent.children) == 2
    assert parent.children == children
    parent.trim()
    assert len(parent.children) == 2
    assert parent.children == children


def test_trim_one_child() -> None:
    parent = Node()
    child1 = Node(parent=parent)
    children = {frozenset({(0, 0)}): child1}
    parent.children = children
    parent.role_move_mapping = {0: 0}
    assert len(parent.children) == 1
    assert parent.children == children
    parent.trim()
    assert len(parent.children) == 1
    assert parent.children == children


def test_trim_parents_parent_is_not_changed() -> None:
    grandparent = Node()
    parent = Node(parent=grandparent)
    sibling = Node(parent=grandparent)
    siblings = {frozenset({(0, 0)}): parent, frozenset({(0, 1)}): sibling}
    grandparent.children = siblings
    grandparent.role_move_mapping = {0: 0}
    child1 = Node(parent=parent)
    child2 = Node(parent=parent)
    children = {frozenset({(0, 0)}): child1, frozenset({(0, 1)}): child2}
    parent.children = children
    parent.role_move_mapping = {0: 0}
    assert len(grandparent.children) == 2
    assert grandparent.children == siblings
    assert len(parent.children) == 2
    assert parent.children == children
    parent.trim()
    assert len(grandparent.children) == 2
    assert grandparent.children == siblings
    assert len(parent.children) == 1
    assert parent.children == {frozenset({(0, 0)}): child1}
