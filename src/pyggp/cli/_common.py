import importlib
import logging
import pathlib
import sys
from typing import Callable, Collection, Iterable, Iterator, Optional, Sequence, Tuple, Type, TypeVar

import rich.progress as rich_progress

import pyggp.game_description_language as gdl
from pyggp.agents import Agent, ArbitraryAgent, HumanAgent, RandomAgent
from pyggp.engine_primitives import Role
from pyggp.exceptions.cli_exceptions import AgentNotFoundCLIError, RolesMismatchCLIError, RulesetNotFoundCLIError

log: logging.Logger = logging.getLogger("pyggp")

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


def determine_file_path(path: pathlib.Path) -> pathlib.Path:
    if (path.exists() and path.is_file()) or not hasattr(sys, "_MEIPASS"):
        return path
    # Disables SLF001 (Private member accessed). Because: pyinstaller sets this attribute.
    base_path = pathlib.Path(sys._MEIPASS).joinpath("games")  # noqa: SLF001
    return base_path.joinpath(path)


def load_ruleset(files: Sequence[pathlib.Path]) -> gdl.Ruleset:
    rules_strs = []
    for file in rich_progress.track(files, description="Loading files", transient=True):
        path = determine_file_path(file)
        try:
            rules_strs.append(path.read_text())
            log.debug("Loaded %s", path)
        except OSError as read_error:
            raise RulesetNotFoundCLIError(path) from read_error
    rules_str = "\n".join(rules_strs)
    tree = gdl.ruleset_parser.parse(rules_str)
    ruleset = gdl.transformer.transform(tree)
    assert isinstance(ruleset, gdl.Ruleset)
    return ruleset


_BUILTIN_AGENTS = {
    "human": HumanAgent,
    "random": RandomAgent,
    "arbitrary": ArbitraryAgent,
}


def get_role_from_str(string: str) -> Role:
    tree = gdl.subrelation_parser.parse(string)
    transformation = gdl.transformer.transform(tree)
    assert isinstance(transformation, gdl.Subrelation)
    return Role(transformation)


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


def check_roles(required_roles: Collection[Role], received_roles: Collection[Role]) -> None:
    if set(required_roles) != set(received_roles):
        raise RolesMismatchCLIError(required_roles, received_roles)
