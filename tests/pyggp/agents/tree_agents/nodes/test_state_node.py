from typing import TYPE_CHECKING, Sequence

import pytest
from pyggp.agents.tree_agents.nodes import StateNode
from pyggp.exceptions.node_exceptions import (
    MultipleDevelopmentsStateNodeError,
    RoleMoveMappingMismatchNodeError,
    StateMismatchNodeError,
)

if TYPE_CHECKING:
    from pyggp.gdl import Development


def test_initializer_raises_on_missing_state() -> None:
    with pytest.raises(TypeError):
        StateNode()


def test_get_records_empty_node() -> None:
    node = StateNode(state=frozenset())
    actual = node.get_records()
    expected = ({0: frozenset()}, {}, {})
    assert actual == expected


def test_get_records_single_move_single_ply() -> None:
    ply_0_node = StateNode(state=frozenset())
    ply_1_node = StateNode(parent=ply_0_node, state=frozenset({0}))
    ply_0_role_move_mapping = {0: 0}
    ply_0_role_move_pairing = frozenset(ply_0_role_move_mapping.items())
    ply_0_children = {ply_0_role_move_pairing: ply_1_node}

    ply_0_node.children = ply_0_children
    ply_0_node.role_move_mapping = ply_0_role_move_mapping

    actual = ply_1_node.get_records()
    expected = ({0: frozenset(), 1: frozenset({0})}, {}, {0: {0: 0}})
    assert actual == expected


def test_get_records_multiple_moves_single_ply() -> None:
    ply_0_node = StateNode(state=frozenset())
    ply_1_node = StateNode(parent=ply_0_node, state=frozenset({0}))
    ply_0_role_move_mapping = {0: 0, 1: 0}
    ply_0_role_move_pairing = frozenset(ply_0_role_move_mapping.items())
    ply_0_children = {ply_0_role_move_pairing: ply_1_node}

    ply_0_node.children = ply_0_children
    ply_0_node.role_move_mapping = ply_0_role_move_mapping

    actual = ply_1_node.get_records()
    expected = ({0: frozenset(), 1: frozenset({0})}, {}, {0: {0: 0, 1: 0}})
    assert actual == expected


def test_get_records_single_move_multiple_ply() -> None:
    ply_0_node = StateNode(state=frozenset())
    ply_0_role_move_mapping = {0: 0}
    ply_0_role_move_pairing = frozenset(ply_0_role_move_mapping.items())
    ply_0_node.role_move_mapping = ply_0_role_move_mapping

    ply_1_node = StateNode(parent=ply_0_node, state=frozenset({0}))
    ply_0_children = {ply_0_role_move_pairing: ply_1_node}
    ply_0_node.children = ply_0_children

    ply_1_role_move_mapping = {0: 1}
    ply_1_role_move_pairing = frozenset(ply_1_role_move_mapping.items())
    ply_1_node.role_move_mapping = ply_1_role_move_mapping

    ply_2_node = StateNode(parent=ply_1_node, state=frozenset({0, 1}))
    ply_1_children = {ply_1_role_move_pairing: ply_2_node}
    ply_1_node.children = ply_1_children

    actual = ply_2_node.get_records()
    expected = ({0: frozenset(), 1: frozenset({0}), 2: frozenset({0, 1})}, {}, {0: {0: 0}, 1: {0: 1}})
    assert actual == expected


def test_get_records_multiple_moves_multiple_ply() -> None:
    ply_0_node = StateNode(state=frozenset())
    ply_0_role_move_mapping = {0: 0, 1: 0}
    ply_0_role_move_pairing = frozenset(ply_0_role_move_mapping.items())
    ply_0_node.role_move_mapping = ply_0_role_move_mapping

    ply_1_node = StateNode(parent=ply_0_node, state=frozenset({0}))
    ply_0_children = {ply_0_role_move_pairing: ply_1_node}
    ply_0_node.children = ply_0_children

    ply_1_role_move_mapping = {0: 1, 1: 1}
    ply_1_role_move_pairing = frozenset(ply_1_role_move_mapping.items())
    ply_1_node.role_move_mapping = ply_1_role_move_mapping

    ply_2_node = StateNode(parent=ply_1_node, state=frozenset({0, 1}))
    ply_1_children = {ply_1_role_move_pairing: ply_2_node}
    ply_1_node.children = ply_1_children

    actual = ply_2_node.get_records()
    expected = ({0: frozenset(), 1: frozenset({0}), 2: frozenset({0, 1})}, {}, {0: {0: 0, 1: 0}, 1: {0: 1, 1: 1}})
    assert actual == expected


def test_get_records_on_done() -> None:
    ply_0_node = StateNode(state=frozenset())
    ply_0_role_move_mapping = {0: 0}
    ply_0_role_move_pairing = frozenset(ply_0_role_move_mapping.items())
    ply_0_node.role_move_mapping = ply_0_role_move_mapping

    ply_1_node = StateNode(parent=ply_0_node, state=frozenset({0}))
    ply_0_children = {ply_0_role_move_pairing: ply_1_node}
    ply_0_node.children = ply_0_children

    assert ply_0_node.is_determined

    actual = ply_0_node.get_records()
    expected = ({0: frozenset()}, {}, {0: {0: 0}})
    assert actual == expected


def test_reconstruct_single_move_single_ply() -> None:
    ply_0_node = StateNode(state=frozenset())
    ply_1_node = StateNode(parent=ply_0_node, state=frozenset({0}))
    ply_0_role_move_mapping = {0: 0}
    ply_0_role_move_pairing = frozenset(ply_0_role_move_mapping.items())
    ply_0_children = {ply_0_role_move_pairing: ply_1_node}
    ply_0_node.children = ply_0_children

    assert ply_0_node.is_expanded
    assert not ply_0_node.is_determined
    assert ply_0_node.role_move_mapping is None
    assert ply_0_node.children == ply_0_children

    developments = (((frozenset({}), {}, ply_0_role_move_mapping), (frozenset({0}), {}, None)),)

    new_root = ply_0_node.reconstruct(*developments)

    assert new_root is not ply_0_node
    assert new_root.parent is ply_0_node
    assert not new_root.is_expanded
    assert ply_0_node.is_determined
    assert ply_0_node.role_move_mapping == ply_0_role_move_mapping
    assert new_root is ply_1_node
    assert new_root is ply_0_node.children[ply_0_role_move_pairing]


def test_reconstruct_multiple_moves_single_ply() -> None:
    ply_0_node = StateNode(state=frozenset())
    ply_1_node = StateNode(parent=ply_0_node, state=frozenset({0}))
    ply_0_role_move_mapping = {0: 0, 1: 0}
    ply_0_role_move_pairing = frozenset(ply_0_role_move_mapping.items())
    ply_0_children = {ply_0_role_move_pairing: ply_1_node}
    ply_0_node.children = ply_0_children

    assert ply_0_node.is_expanded
    assert not ply_0_node.is_determined
    assert ply_0_node.role_move_mapping is None
    assert ply_0_node.children == ply_0_children

    developments = (((frozenset({}), {}, ply_0_role_move_mapping), (frozenset({0}), {}, None)),)

    new_root = ply_0_node.reconstruct(*developments)

    assert new_root is not ply_0_node
    assert new_root.parent is ply_0_node
    assert not new_root.is_expanded
    assert ply_0_node.is_determined
    assert ply_0_node.role_move_mapping == ply_0_role_move_mapping
    assert new_root is ply_1_node
    assert new_root is ply_0_node.children[ply_0_role_move_pairing]


def test_reconstruct_single_move_multiple_ply() -> None:
    ply_0_node = StateNode(state=frozenset())
    ply_1_node = StateNode(parent=ply_0_node, state=frozenset({0}))
    ply_0_role_move_mapping = {0: 0}
    ply_0_role_move_pairing = frozenset(ply_0_role_move_mapping.items())
    ply_0_children = {ply_0_role_move_pairing: ply_1_node}
    ply_0_node.children = ply_0_children

    ply_2_node = StateNode(parent=ply_1_node, state=frozenset({0, 1}))
    ply_1_role_move_mapping = {0: 1}
    ply_1_role_move_pairing = frozenset(ply_1_role_move_mapping.items())
    ply_1_children = {ply_1_role_move_pairing: ply_2_node}
    ply_1_node.children = ply_1_children

    assert ply_0_node.is_expanded
    assert not ply_0_node.is_determined
    assert ply_0_node.role_move_mapping is None
    assert ply_0_node.children == ply_0_children

    assert ply_1_node.is_expanded
    assert not ply_1_node.is_determined
    assert ply_1_node.role_move_mapping is None
    assert ply_1_node.children == ply_1_children

    developments = (
        (
            (frozenset({}), {}, ply_0_role_move_mapping),
            (frozenset({0}), {}, ply_1_role_move_mapping),
            (frozenset({0, 1}), {}, None),
        ),
    )

    new_root = ply_1_node.reconstruct(*developments)

    assert new_root is not ply_0_node
    assert new_root.parent is ply_1_node
    assert not new_root.is_expanded
    assert ply_0_node.is_determined
    assert ply_0_node.role_move_mapping == ply_0_role_move_mapping
    assert new_root is ply_2_node
    assert new_root is ply_1_node.children[ply_1_role_move_pairing]


def test_reconstruct_single_move_multiple_ply_from_root() -> None:
    ply_0_node = StateNode(state=frozenset())
    ply_1_node = StateNode(parent=ply_0_node, state=frozenset({0}))
    ply_0_role_move_mapping = {0: 0}
    ply_0_role_move_pairing = frozenset(ply_0_role_move_mapping.items())
    ply_0_children = {ply_0_role_move_pairing: ply_1_node}
    ply_0_node.children = ply_0_children

    ply_2_node = StateNode(parent=ply_1_node, state=frozenset({0, 1}))
    ply_1_role_move_mapping = {0: 1}
    ply_1_role_move_pairing = frozenset(ply_1_role_move_mapping.items())
    ply_1_children = {ply_1_role_move_pairing: ply_2_node}
    ply_1_node.children = ply_1_children

    assert ply_0_node.is_expanded
    assert not ply_0_node.is_determined
    assert ply_0_node.role_move_mapping is None
    assert ply_0_node.children == ply_0_children

    assert ply_1_node.is_expanded
    assert not ply_1_node.is_determined
    assert ply_1_node.role_move_mapping is None
    assert ply_1_node.children == ply_1_children

    developments = (
        (
            (frozenset({}), {}, ply_0_role_move_mapping),
            (frozenset({0}), {}, ply_1_role_move_mapping),
            (frozenset({0, 1}), {}, None),
        ),
    )

    new_root = ply_0_node.reconstruct(*developments)

    assert new_root is not ply_0_node
    assert new_root is not ply_1_node
    assert new_root is ply_2_node
    assert new_root.parent is ply_1_node
    assert not new_root.is_expanded
    assert ply_0_node.is_determined
    assert ply_0_node.role_move_mapping == ply_0_role_move_mapping
    assert new_root is ply_1_node.children[ply_1_role_move_pairing]


def test_reconstruct_multiple_moves_multiple_ply() -> None:
    ply_0_node = StateNode(state=frozenset())
    ply_1_node = StateNode(parent=ply_0_node, state=frozenset({0}))
    ply_0_role_move_mapping = {0: 0, 1: 0}
    ply_0_role_move_pairing = frozenset(ply_0_role_move_mapping.items())
    ply_0_children = {ply_0_role_move_pairing: ply_1_node}
    ply_0_node.children = ply_0_children

    ply_2_node = StateNode(parent=ply_1_node, state=frozenset({0, 1}))
    ply_1_role_move_mapping = {0: 1, 1: 1}
    ply_1_role_move_pairing = frozenset(ply_1_role_move_mapping.items())
    ply_1_children = {ply_1_role_move_pairing: ply_2_node}
    ply_1_node.children = ply_1_children

    assert ply_0_node.is_expanded
    assert not ply_0_node.is_determined
    assert ply_0_node.role_move_mapping is None
    assert ply_0_node.children == ply_0_children

    assert ply_1_node.is_expanded
    assert not ply_1_node.is_determined
    assert ply_1_node.role_move_mapping is None
    assert ply_1_node.children == ply_1_children

    developments = (
        (
            (frozenset({}), {}, ply_0_role_move_mapping),
            (frozenset({0}), {}, ply_1_role_move_mapping),
            (frozenset({0, 1}), {}, None),
        ),
    )

    new_root = ply_1_node.reconstruct(*developments)

    assert new_root is not ply_0_node
    assert new_root is not ply_1_node
    assert new_root is ply_2_node
    assert new_root.parent is ply_1_node
    assert not new_root.is_expanded
    assert ply_0_node.is_determined
    assert ply_0_node.role_move_mapping == ply_0_role_move_mapping
    assert new_root is ply_1_node.children[ply_1_role_move_pairing]


def test_reconstruct_multiple_moves_multiple_ply_from_root() -> None:
    ply_0_node = StateNode(state=frozenset())
    ply_1_node = StateNode(parent=ply_0_node, state=frozenset({0}))
    ply_0_role_move_mapping = {0: 0, 1: 0}
    ply_0_role_move_pairing = frozenset(ply_0_role_move_mapping.items())
    ply_0_children = {ply_0_role_move_pairing: ply_1_node}
    ply_0_node.children = ply_0_children

    ply_2_node = StateNode(parent=ply_1_node, state=frozenset({0, 1}))
    ply_1_role_move_mapping = {0: 1, 1: 1}
    ply_1_role_move_pairing = frozenset(ply_1_role_move_mapping.items())
    ply_1_children = {ply_1_role_move_pairing: ply_2_node}
    ply_1_node.children = ply_1_children

    assert ply_0_node.is_expanded
    assert not ply_0_node.is_determined
    assert ply_0_node.role_move_mapping is None
    assert ply_0_node.children == ply_0_children

    assert ply_1_node.is_expanded
    assert not ply_1_node.is_determined
    assert ply_1_node.role_move_mapping is None
    assert ply_1_node.children == ply_1_children

    developments = (
        (
            (frozenset({}), {}, ply_0_role_move_mapping),
            (frozenset({0}), {}, ply_1_role_move_mapping),
            (frozenset({0, 1}), {}, None),
        ),
    )

    new_root = ply_0_node.reconstruct(*developments)

    assert new_root is not ply_0_node
    assert new_root is not ply_1_node
    assert new_root is ply_2_node
    assert new_root.parent is ply_1_node
    assert not new_root.is_expanded
    assert ply_0_node.is_determined
    assert ply_0_node.role_move_mapping == ply_0_role_move_mapping
    assert new_root is ply_1_node.children[ply_1_role_move_pairing]


def test_reconstruct_raises_on_multiple_developments() -> None:
    developments = (
        ((frozenset({}), None, {0: 0}), (frozenset({0}), None, None)),
        ((frozenset({}), None, {0: 1}), (frozenset({1}), None, None)),
    )

    node = StateNode(state=frozenset())
    with pytest.raises(MultipleDevelopmentsStateNodeError):
        node.reconstruct(*developments)


def test_reconstruct_raises_on_state_mismatch() -> None:
    developments: Sequence[Development] = (((frozenset({}), None, None),),)

    node = StateNode(state=frozenset({0}))
    with pytest.raises(StateMismatchNodeError):
        node.reconstruct(*developments)


def test_reconstruct_raises_on_role_move_mapping_mismatch() -> None:
    developments: Sequence[Development] = (
        (
            (frozenset({}), None, {0: 0}),
            (frozenset({0}), None, None),
        ),
    )

    node = StateNode(state=frozenset(), role_move_mapping={0: 1})
    with pytest.raises(RoleMoveMappingMismatchNodeError):
        node.reconstruct(*developments)
