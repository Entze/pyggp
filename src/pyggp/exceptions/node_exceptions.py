"""Exceptions regarding nodes."""
from typing import Optional

from pyggp.gdl import ConcreteRoleMoveMapping, State


class NodeError(Exception):
    """Base class for all exceptions regarding nodes."""


class DevelopmentMismatchNodeError(NodeError):
    """Base class for all exceptions regarding development mismatches."""


class StateMismatchNodeError(DevelopmentMismatchNodeError):
    """State of node and development do not match."""

    def __init__(
        self,
        /,
        development_state: Optional[State] = None,
        node_state: Optional[State] = None,
        ply: Optional[int] = None,
    ) -> None:
        """Initializes StateMismatchNodeError.

        Args:
            development_state: State in development
            node_state: State in node
            ply: Ply where mismatch occurred

        """
        mismatching_development_state = (
            set(development_state - node_state) if development_state is not None and node_state is not None else None
        )
        mismatching_node_state = (
            set(node_state - development_state) if development_state is not None and node_state is not None else None
        )
        mismatching_development_message = (
            f" in development but not in node {mismatching_development_state}"
            if mismatching_development_state is not None
            else ""
        )
        mismatching_node_message = (
            f" in node but not in development {mismatching_node_state}" if mismatching_node_state is not None else ""
        )
        ply_message = f" during ply {ply}" if ply is not None else ""
        message = f"State mismatch{ply_message}{mismatching_development_message}{mismatching_node_message}"
        super().__init__(message)


class RoleMoveMappingMismatchNodeError(DevelopmentMismatchNodeError):
    """Role-move mapping of node and development do not match."""

    def __init__(
        self,
        /,
        development_role_move_mapping: Optional[ConcreteRoleMoveMapping] = None,
        node_role_move_mapping: Optional[ConcreteRoleMoveMapping] = None,
        ply: Optional[int] = None,
    ) -> None:
        """Initializes RoleMoveMappingMismatchNodeError.

        Args:
            development_role_move_mapping: Role-move mapping in development
            node_role_move_mapping: Role-move mapping in node
            ply: Ply where mismatch occurred

        """
        mismatching_development_role_move_mapping = (
            {k: node_role_move_mapping[k] for k in set(development_role_move_mapping) - set(node_role_move_mapping)}
            if development_role_move_mapping is not None and node_role_move_mapping is not None
            else None
        )
        mismatching_node_role_move_mapping = (
            {
                k: development_role_move_mapping[k]
                for k in set(node_role_move_mapping) - set(development_role_move_mapping)
            }
            if development_role_move_mapping is not None and node_role_move_mapping is not None
            else None
        )
        mismatching_development_role_move_mapping_message = (
            f" in development but not in node {mismatching_development_role_move_mapping}"
            if mismatching_development_role_move_mapping is not None
            else ""
        )
        mismatching_node_role_move_mapping_message = (
            f" in node but not in development {mismatching_node_role_move_mapping}"
            if mismatching_node_role_move_mapping is not None
            else ""
        )
        ply_message = f" during ply {ply}" if ply is not None else ""
        message = (
            "Role-move mapping mismatch"
            f"{ply_message}"
            f"{mismatching_development_role_move_mapping_message}"
            f"{mismatching_node_role_move_mapping_message}"
        )
        super().__init__(message)


class StateNodeError(NodeError):
    """Base class for all exceptions regarding state node."""


class MultipleDevelopmentsStateNodeError(StateNodeError):
    """More than one development provided for state node."""
