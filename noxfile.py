import fnmatch
import functools
import pathlib
import platform
import sys
from typing import (
    Callable,
    Collection,
    Final,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Tuple,
    TypedDict,
)

import nox
import nox as nox_session
import tomli as tomllib
from typing_extensions import NotRequired, TypeAlias

PYTHON_VERSIONS: Final[List[str]] = ["3.9", "3.10", "3.11", "3.12", "pypy3.9"]
PYTHON_VERSIONS_SHORT_NAMES: Final[Mapping[str, str]] = {
    "3.9": "py39",
    "3.10": "py310",
    "3.11": "py311",
    "3.12": "py312",
    "pypy-3.9": "pypy39",
}
PYTHON_IMPLEMENTATIONS_SHORT_NAMES: Final[Mapping[str, str]] = {"cpython": "py", "pypy": "pypy"}
__python_implementation = platform.python_implementation()
__python_major, __python_minor, *_ = sys.version_info

PYTHON_VERSION_LOCAL: Final[str] = (
    f"{__python_implementation.lower() if __python_implementation != 'CPython' else ''}"
    f"{__python_major}.{__python_minor}"
)
PYTHON_VERSION_LOCAL_SHORT_NAME: Final[str] = (
    PYTHON_IMPLEMENTATIONS_SHORT_NAMES.get(__python_implementation.lower(), "python")
    + str(__python_major)
    + str(__python_minor)
)

IDENTIFIERS: MutableMapping[str, str] = {}
VERSIONS: MutableMapping[str, Optional[str]] = {}

with pathlib.Path("pyproject.toml").open(mode="rb") as pyproject_toml_file, pathlib.Path("poetry.lock").open(
    mode="rb",
) as poetry_lock_file:
    pyproject_toml = tomllib.load(pyproject_toml_file)
    poetry_lock = tomllib.load(poetry_lock_file)
    for group in pyproject_toml["tool"]["poetry"]["group"]:
        for dependency, data in pyproject_toml["tool"]["poetry"]["group"][group]["dependencies"].items():
            name = dependency
            lock_info, *_ = (package for package in poetry_lock["package"] if package["name"] == name)
            version = lock_info["version"]
            VERSIONS[dependency] = f"=={version}"
            if isinstance(data, str):
                IDENTIFIERS[dependency] = dependency
            elif isinstance(data, dict):
                IDENTIFIERS[dependency] = f"{dependency}[{','.join(data['extras'])}]"


class Args(TypedDict):
    static_opts: NotRequired[Sequence[str]]
    allow_opts: NotRequired[Sequence[str]]
    default_opts: NotRequired[Sequence[str]]
    static_targets: NotRequired[Sequence[str]]
    allow_targets: NotRequired[Sequence[str]]
    default_targets: NotRequired[Sequence[str]]
    success_codes: NotRequired[Collection[int]]


ALL_TARGETS: Sequence[str] = ("src", "src/*", "tests", "tests/*", "noxfile.py")

ArgConfig: TypeAlias = Mapping[str, Mapping[str, Args]]

ARGS: Final[ArgConfig] = dict(
    unittests=dict(
        pytest=Args(
            allow_targets=("tests",),
            default_targets=("tests",),
        ),
    ),
    doctests=dict(
        pytest=Args(
            static_opts=("--doctest-modules", "--ignore-glob=test_*.py"),
            allow_targets=("src",),
            default_targets=("src",),
        ),
    ),
    doclint=dict(
        docformatter=Args(
            static_opts=("--check", "--diff", "--recursive"),
            allow_targets=ALL_TARGETS,
            default_targets=("src", "tests", "noxfile.py"),
        ),
        ruff=Args(
            static_opts=("check", "--select", "D"),
            allow_opts=("--show-fixes", "--statistics"),
            allow_targets=ALL_TARGETS,
            default_targets=("src", "tests", "noxfile.py"),
        ),
    ),
    lint=dict(
        black=Args(
            static_opts=("--check",),
            allow_targets=ALL_TARGETS,
            default_targets=("src", "tests", "prof", "noxfile.py"),
        ),
        ruff=Args(
            static_opts=("check",),
            allow_opts=("--show-fixes", "--statistics"),
            allow_targets=ALL_TARGETS,
            default_targets=("src", "tests", "prof", "noxfile.py"),
        ),
    ),
    typecheck=dict(
        mypy=Args(
            allow_opts=(
                "--strict",
                "--config-file",
                "pyproject.toml",
            ),
            default_opts=(
                "--config-file",
                "pyproject.toml",
            ),
            allow_targets=ALL_TARGETS,
            default_targets=("src",),
        ),
    ),
    fix=dict(
        black=Args(
            allow_targets=ALL_TARGETS,
            default_targets=("src", "tests", "prof", "noxfile.py"),
        ),
        docformatter=Args(
            static_opts=(
                "--in-place",
                "--recursive",
            ),
            allow_targets=ALL_TARGETS,
            default_targets=("src", "tests", "noxfile.py"),
        ),
        ruff=Args(
            static_opts=("check", "--extend-select", "D", "--fix-only", "--exit-zero"),
            allow_targets=ALL_TARGETS,
            default_targets=("src", "tests", "prof", "noxfile.py"),
        ),
    ),
    coverage=dict(
        coverage=Args(
            allow_opts=("run", "-m", "report", "xml", "html", "--rcfile=pyproject.toml"),
            allow_targets=("pytest",),
        ),
        pytest=Args(
            allow_opts=("--doctest-modules",),
            allow_targets=ALL_TARGETS,
        ),
    ),
)


def _install(session: nox.Session, *dependencies: str) -> None:
    for dependency in dependencies:
        if dependency not in VERSIONS:
            session.error(f"Dependency {dependency} not found in pyproject.toml")
    session.install(*(f"{dependency}{VERSIONS[dependency]}" for dependency in dependencies))


def _filter(
    session: nox.Session,
    context: str,
    program: str,
    posargs: Sequence[str],
) -> Tuple[Sequence[str], Sequence[str]]:
    opts = list(ARGS[context][program].get("static_opts", ()))
    opt_defaults = True
    targets = list(ARGS[context][program].get("static_targets", ()))
    target_defaults = True
    for arg in posargs:
        if arg in ARGS[context][program].get("allow_opts", ()):
            session.debug("Allowing opt: %s", arg)
            opts.append(arg)
            opt_defaults = False
        else:
            session.debug(
                "Disallowed opt: %s, did not match with %s",
                arg,
                ARGS[context][program].get("allow_opts", ()),
            )
        if any(fnmatch.fnmatch(arg, pattern) for pattern in ARGS[context][program].get("allow_targets", ())):
            session.debug("Allowed target: %s", arg)
            targets.append(arg)
            target_defaults = False
        else:
            session.debug(
                "Disallowed target: %s, did not match with %s",
                arg,
                ARGS[context][program].get("allow_targets", ()),
            )
    if opt_defaults:
        opts.extend(ARGS[context][program].get("default_opts", ()))
    if target_defaults:
        targets.extend(ARGS[context][program].get("default_targets", ()))
    return opts, targets


def _run(session: nox.Session, context: str, program: str, posargs: Sequence[str]) -> None:
    session.debug("Received: context=%s, program=%s, posargs=%s", context, program, posargs)
    opts, targets = _filter(session, context, program, posargs)
    session.debug("Filtered: opts=%s, targets=%s", opts, targets)
    success_codes = ARGS[context][program].get("success_codes", (0,))
    session.debug("Success codes: %s", success_codes)
    session.run(program, *opts, *targets, success_codes=success_codes)


@nox_session.session(tags=["checks", "tests"], python=PYTHON_VERSIONS)
def unittests(session: nox.Session) -> None:
    session.install(".")
    dependencies = ("pytest", "pytest-unordered")
    programs = ("pytest",)
    _install(session, *dependencies)
    run = functools.partial(_run, session=session, context="unittests", posargs=session.posargs)
    for program in programs:
        run(program=program)


@nox_session.session(tags=["checks", "tests"], python=PYTHON_VERSIONS)
def doctests(session: nox.Session) -> None:
    session.install(".")
    dependencies = ("pytest",)
    programs = ("pytest",)
    _install(session, *dependencies)
    run = functools.partial(_run, session=session, context="doctests", posargs=session.posargs)
    for program in programs:
        run(program=program)


@nox_session.session(tags=["checks", "ci"])
def doclint(session: nox.Session) -> None:
    session.install(".")
    dependencies = ("docformatter", "ruff")
    programs = ("docformatter", "ruff")
    _install(session, *dependencies)
    run = functools.partial(_run, session=session, context="doclint", posargs=session.posargs)
    for program in programs:
        run(program=program)


@nox_session.session(tags=["checks", "ci"])
def lint(session: nox.Session) -> None:
    session.install(".")
    dependencies = ("black", "ruff")
    programs = ("black", "ruff")
    _install(session, *dependencies)
    run = functools.partial(_run, session=session, context="lint", posargs=session.posargs)
    for program in programs:
        run(program=program)


@nox_session.session(tags=["checks", "ci"])
def typecheck(session: nox.Session) -> None:
    session.install(".")
    dependencies = ("mypy", "pytest")
    programs = ("mypy",)
    _install(session, *dependencies)
    run = functools.partial(_run, session=session, context="typecheck", posargs=session.posargs)
    for program in programs:
        run(program=program)


@nox_session.session
def fix(session: nox.Session) -> None:
    session.install(".")
    dependencies = ("black", "docformatter", "ruff")
    programs = ("black", "docformatter", "ruff", "black")
    _install(session, *dependencies)
    run: Callable[[str], None] = functools.partial(_run, session=session, context="fix", posargs=session.posargs)
    for program in programs:
        run(program=program)


@nox_session.session
def coverage(session: nox.Session) -> None:
    session.install(".")
    dependencies = ("coverage", "pytest")
    _install(session, *dependencies)

    pytest_opts, pytest_targets = _filter(session, "coverage", "pytest", session.posargs)
    _run(
        session,
        "coverage",
        "coverage",
        posargs=("run", "-m", "pytest", *pytest_opts, *pytest_targets, *session.posargs),
    )
    _run(session, "coverage", "coverage", posargs=("report", "--rcfile=pyproject.toml", "-m", *session.posargs))
    _run(session, "coverage", "coverage", posargs=("xml", *session.posargs))


@nox_session.session
def build(session: nox.Session) -> None:
    session.install(".")
    dependencies = ("pyinstaller",)
    _install(session, *dependencies)
    src_games_data = "src/games"
    dest_games_data = "games"
    src_visualizer_data = "src/visualizers"
    dest_visualizer_data = "visualizers"
    data_seq = {src_games_data: dest_games_data, src_visualizer_data: dest_visualizer_data}
    sep = ":" if platform.system() != "Windows" else ";"
    args = [
        "pyinstaller",
        "--onefile",
    ]
    for src, dest in data_seq.items():
        args.extend(
            (
                "--add-data",
                f"{src}{sep}{dest}",
            ),
        )
    args.extend(
        (
            "--collect-all",
            "clingo",
            "--name",
            "pyggp",
            "src/pyggp/__main__.py",
        ),
    )

    session.run(
        *args,
        env={"PYTHONOPTIMIZE": "1"},
    )
