import fnmatch
import functools
import platform
import sys
from typing import Callable, Collection, List, Mapping, MutableMapping, Optional, Sequence, Tuple, TypeAlias, TypedDict

import nox
import tomli as tomllib
from typing_extensions import Final, NotRequired

PYTHON_VERSIONS: Final[List[str]] = ["3.8", "3.9", "3.10", "3.11", "pypy-3.8", "pypy-3.9"]
PYTHON_VERSIONS_SHORT_NAMES: Final[Mapping[str, str]] = {
    "3.8": "py38",
    "3.9": "py39",
    "3.10": "py310",
    "3.11": "py311",
    "pypy-3.8": "pypy38",
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

VERSIONS: MutableMapping[str, Optional[str]] = dict()

with open("pyproject.toml", "rb") as f:
    pyproject_toml = tomllib.load(f)
    VERSIONS.update(pyproject_toml["tool"]["poetry"]["group"]["dev"]["dependencies"])


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
    unittest=dict(
        pytest=Args(
            allow_targets=("tests",),
            default_targets=(
                "tests",
                "tests/*",
            ),
        )
    ),
    doctest=dict(
        pytest=Args(
            static_opts=("--doctest-modules",),
            allow_targets=("src",),
            default_targets=("src",),
        )
    ),
    lint=dict(
        black=Args(
            static_opts=("--check",),
            allow_targets=ALL_TARGETS,
            default_targets=("src", "tests", "noxfile.py"),
        ),
        docformatter=Args(
            static_opts=("--check", "--diff"),
            allow_targets=ALL_TARGETS,
            default_targets=("src", "tests", "noxfile.py"),
        ),
        ruff=Args(
            static_opts=("check",),
            allow_opts=("--show-fixes", "--statistics"),
            allow_targets=ALL_TARGETS,
            default_targets=("src", "tests", "noxfile.py"),
        ),
        pytest=Args(
            static_opts=("--doctest-modules",),
            allow_targets=ALL_TARGETS,
            default_targets=("src",),
            success_codes=(0, 5),
        ),
    ),
    typecheck=dict(
        mypy=Args(
            allow_opts=("--strict",),
            default_opts=("--strict",),
            allow_targets=ALL_TARGETS,
            default_targets=("src", "tests", "noxfile.py"),
        ),
    ),
    fix=dict(
        black=Args(
            allow_targets=ALL_TARGETS,
            default_targets=("src", "tests", "noxfile.py"),
        ),
        docformatter=Args(
            static_opts=("--in-place",),
            allow_targets=ALL_TARGETS,
            default_targets=("src", "tests", "noxfile.py"),
        ),
        ruff=Args(
            static_opts=("check", "--fix"),
            allow_targets=ALL_TARGETS,
            default_targets=("src", "tests", "noxfile.py"),
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
    build=dict(
        shiv=Args(
            allow_opts=(
                "--console-script",
                "pyggp",
                "--compressed",
                "--output-file",
                *(f"pyggp-{PY}" for PY in PYTHON_VERSIONS_SHORT_NAMES.values()),
                "--python",
                "/usr/bin/env -S python3 -O",
                "/usr/bin/env python3",
                "/usr/bin/env -S python -O",
                "/usr/bin/env python",
            ),
            default_opts=(
                "--console-script",
                "pyggp",
                "--compressed",
                "--output-file",
                f"pyggp-{PYTHON_VERSION_LOCAL_SHORT_NAME}",
                "--python",
                f"/usr/bin/env -S python3 -O",
            ),
            allow_targets=(".", *ALL_TARGETS),
            default_targets=(".",),
        ),
    ),
)


def _install(session: nox.Session, *dependencies: str) -> None:
    for dependency in dependencies:
        if dependency not in VERSIONS:
            session.error(f"Dependency {dependency} not found in pyproject.toml")
    session.install(*(f"{dependency}{VERSIONS[dependency]}" for dependency in dependencies))


def _filter(
    session: nox.Session, context: str, program: str, posargs: Sequence[str]
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
                "Disallowed opt: %s, did not match with %s", arg, ARGS[context][program].get("allow_opts", ())
            )
        if any(fnmatch.fnmatch(arg, pattern) for pattern in ARGS[context][program].get("allow_targets", ())):
            session.debug("Allowed target: %s", arg)
            targets.append(arg)
            target_defaults = False
        else:
            session.debug(
                "Disallowed target: %s, did not match with %s", arg, ARGS[context][program].get("allow_targets", ())
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


@nox.session(tags=["checks", "tests"], python=PYTHON_VERSIONS)
def unittests(session: nox.Session) -> None:
    session.install(".")
    programs = ("pytest",)
    _install(session, *programs)
    run = functools.partial(_run, session=session, context="unittests", posargs=session.posargs)
    for program in programs:
        run(program)


@nox.session(tags=["checks", "tests"])
def doctests(session: nox.Session) -> None:
    session.install(".")
    programs = ("pytest",)
    _install(session, *programs)
    run = functools.partial(_run, session=session, context="doctests", posargs=session.posargs)
    for program in programs:
        run(program=program)


@nox.session(tags=["checks", "ci"])
def lint(session: nox.Session) -> None:
    session.install(".")
    programs = ("black", "docformatter", "pytest", "ruff")
    _install(session, *programs)
    run = functools.partial(_run, session=session, context="lint", posargs=session.posargs)
    for program in programs:
        run(program=program)


@nox.session(tags=["checks", "ci"])
def typecheck(session: nox.Session) -> None:
    session.install(".")
    programs = ("mypy",)
    _install(session, *programs, "pytest")
    run = functools.partial(_run, session=session, context="typecheck", posargs=session.posargs)
    for program in programs:
        run(program=program)


@nox.session
def fix(session: nox.Session) -> None:
    session.install(".")
    programs = ("black", "docformatter", "ruff")
    _install(session, *programs)
    run: Callable[[str], None] = functools.partial(_run, session=session, context="fix", posargs=session.posargs)
    for program in programs:
        run(program=program)


@nox.session
def coverage(session: nox.Session) -> None:
    session.install(".")
    _install(session, "coverage", "pytest")

    pytest_opts, pytest_targets = _filter(session, "coverage", "pytest", session.posargs)
    _run(
        session,
        "coverage",
        "coverage",
        posargs=("run", "-m", "pytest", *pytest_opts, *pytest_targets, *session.posargs),
    )
    _run(session, "coverage", "coverage", posargs=("report", "--rcfile=pyproject.toml", "-m", *session.posargs))
    _run(session, "coverage", "coverage", posargs=("xml", *session.posargs))


@nox.session
def build(session: nox.Session) -> None:
    programs = ("shiv",)
    _install(session, *programs)
    run = functools.partial(_run, session=session, context="build", posargs=session.posargs)
    for program in programs:
        run(program)
