"""Exceptions regarding the command line interface."""
import pathlib
from typing import Iterable, Optional

from pyggp.engine_primitives import Role


class CLIError(Exception):
    """Base class for exceptions regarding the command line interface."""


class RulesetNotFoundCLIError(CLIError):
    """Raised when a ruleset_resource is not found."""

    def __init__(self, ruleset_resource: Optional[pathlib.Path] = None) -> None:
        """Initializes RulesetNotFoundCLIError.

        Args:
            ruleset_resource: The ruleset that was not found.

        """
        ruleset_message = f" '{ruleset_resource}'" if ruleset_resource else ""
        message = f"Ruleset{ruleset_message} not found"

        super().__init__(message)


class RolesMismatchCLIError(CLIError):
    """Roles in the registry do not match the roles in the ruleset."""

    def __init__(
        self,
        ruleset_roles: Optional[Iterable[Role]] = None,
        registry_roles: Optional[Iterable[Role]] = None,
    ) -> None:
        """Initializes RolesMismatchCLIError.

        Args:
            ruleset_roles: Roles in the ruleset.
            registry_roles: Roles in the registry.

        """
        superfluous_message = (
            f" superfluous roles: {set(registry_roles) - set(ruleset_roles)}"
            if registry_roles is not None and ruleset_roles is not None
            else ""
        )
        missing_message = (
            f" missing roles: {set(ruleset_roles) - set(registry_roles)}"
            if registry_roles is not None and ruleset_roles is not None
            else ""
        )
        message = f"Roles mismatch{missing_message}{superfluous_message}"

        super().__init__(message)


class AgentNotFoundCLIError(CLIError):
    """Agent is not found."""

    def __init__(self, name: Optional[str] = None) -> None:
        """Initializes AgentNotFoundCLIError."""
        agent_message = f" '{name}'" if name else ""
        message = f"Agent{agent_message} not found"

        super().__init__(message)
