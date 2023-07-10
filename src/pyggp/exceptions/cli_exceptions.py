"""Exceptions regarding the command line interface."""
import pathlib
from typing import Iterable, Mapping, Optional, Sequence

from pyggp._logging import rich
from pyggp.cli.argument_specification import ArgumentSpecification
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

    def __init__(self, spec: Optional[ArgumentSpecification] = None) -> None:
        """Initializes AgentNotFoundCLIError."""
        agent_message = f" '{rich(spec)}'" if spec else ""
        message = f"Agent{agent_message} not found"

        super().__init__(message)


class VisualizerSpecificationCLIError(CLIError):
    """Specification of visualizer is not valid."""

    def __init__(
        self,
        problem: Optional[str] = None,
        name: Optional[str] = None,
        args: Optional[Sequence[str]] = None,
        kwargs: Optional[Mapping[str, str]] = None,
    ) -> None:
        """Initializes VisualizerSpecificationError."""
        name_message = f"{name}" if name else ""
        args_message = f"{','.join(args)}" if args else ""
        kwargs_message = f"{','.join(f'{k}={v}' for k, v in kwargs.items())}" if kwargs else ""
        if args is not None and args and kwargs is not None and kwargs:
            arguments_message = f"({args_message},{kwargs_message})"
        elif args is not None and args:
            arguments_message = f"({args_message})"
        elif kwargs is not None and kwargs:
            arguments_message = f"({kwargs_message})"
        else:
            arguments_message = ""
        visualizer_message = f"{name_message}{arguments_message}"
        problem_message = f" {problem}" if problem else " could not be instantiated"

        message = f"Visualizer '{visualizer_message}'{problem_message}"

        super().__init__(message)


class VisualizerNotFoundCLIError(VisualizerSpecificationCLIError):
    """Visualizer is not found."""

    def __init__(
        self,
        name: Optional[str] = None,
        args: Optional[Sequence[str]] = None,
        kwargs: Optional[Mapping[str, str]] = None,
    ) -> None:
        """Initializes VisualizerNotFoundCLIError."""
        super().__init__("not found", name, args, kwargs)
