import importlib
import logging
from typing import Callable, Collection, Iterable, Iterator, Optional, Tuple, Type, TypeVar

from pyggp.agents import Agent, ArbitraryAgent, HumanAgent, RandomAgent
from pyggp.exceptions.cli_exceptions import AgentNotFoundCLIError, RolesMismatchCLIError, RulesetNotFoundCLIError
from pyggp.games import minipoker_ruleset as minipoker
from pyggp.games import nim_ruleset as nim
from pyggp.games import rock_paper_scissors_ruleset as rock_paper_scissors
from pyggp.games import tic_tac_toe_ruleset as tic_tac_toe
from pyggp.gdl import ConcreteRole, Ruleset

_INFO_VERBOSITY = 0
_WARNING_VERBOSITY = -1
_ERROR_VERBOSITY = -2
_CRITICAL_VERBOSITY = -3


def determine_log_level(verbose: int = 0, quiet: int = 0) -> int:
    verbosity = verbose - quiet
    if verbosity > _INFO_VERBOSITY:
        log_level = logging.DEBUG
    elif verbosity == _INFO_VERBOSITY:
        log_level = logging.INFO
    elif verbosity == _WARNING_VERBOSITY:
        log_level = logging.WARNING
    elif verbosity == _ERROR_VERBOSITY:
        log_level = logging.ERROR
    elif verbosity == _CRITICAL_VERBOSITY:
        log_level = logging.CRITICAL
    else:
        log_level = logging.FATAL

    return log_level


V = TypeVar("V")
K = TypeVar("K")


def parse_registry(
    registry: Iterable[str],
    default_value: V,
    str_to_key: Optional[Callable[[str], K]] = None,
    str_to_value: Optional[Callable[[str], V]] = None,
    *,
    mapping_delimiter: Optional[str] = None,
) -> Iterator[Tuple[K, V]]:
    if mapping_delimiter is None:
        mapping_delimiter = "="
    assert mapping_delimiter is not None
    if str_to_key is None:
        # Disables mypy misc. Because don't fight the typechecker.
        def str_to_key(string: str) -> str:  # type: ignore[misc]
            return string

    assert str_to_key is not None
    assert callable(str_to_key)
    if str_to_value is None:
        # Disables mypy misc. Because don't fight the typechecker.
        def str_to_value(string: str) -> str:  # type: ignore[misc]
            return string

        assert isinstance(default_value, str)

    assert str_to_value is not None
    assert callable(str_to_value)
    for entry in registry:
        if mapping_delimiter in entry:
            key_str, value_str = entry.split(sep=mapping_delimiter, maxsplit=1)
            key = str_to_key(key_str)
            value = str_to_value(value_str)
        else:
            key_str = entry
            key = str_to_key(key_str)
            value = default_value
        yield key, value


def load_ruleset(ruleset_resource: str) -> Ruleset:
    rrl = ruleset_resource.lower()
    if rrl == "nim":
        return nim
    if rrl == "tic-tac-toe":
        return tic_tac_toe
    if rrl == "rock-paper-scissors":
        return rock_paper_scissors
    if rrl == "minipoker":
        return minipoker
    raise RulesetNotFoundCLIError(ruleset_resource) from None


_BUILTIN_AGENTS = {
    "human": HumanAgent,
    "random": RandomAgent,
    "arbitrary": ArbitraryAgent,
}


def get_agentname_from_str(string: str) -> str:
    for builtin_agent_name in _BUILTIN_AGENTS:
        for variation in (string, string.casefold().replace("agent", "")):
            if variation.casefold() == builtin_agent_name.casefold():
                return builtin_agent_name.capitalize()

    return string


def load_agent_by_name(name: str) -> Type[Agent]:
    name_casefold = name.casefold()
    for builtin_agent_name, builtin_agent_type in _BUILTIN_AGENTS.items():
        if name_casefold == builtin_agent_name.casefold():
            return builtin_agent_type
    try:
        module_name, class_name = name.rsplit(".", maxsplit=1)
        module = importlib.import_module(module_name)
        agent_type: Type[Agent] = getattr(module, class_name)
    except (ValueError, ModuleNotFoundError, AttributeError):
        raise AgentNotFoundCLIError(name) from None
    return agent_type


def check_roles(required_roles: Collection[ConcreteRole], received_roles: Collection[ConcreteRole]) -> None:
    if set(required_roles) != set(received_roles):
        raise RolesMismatchCLIError(required_roles, received_roles)
