import logging
import platform
import sys
from typing import List, Mapping, MutableMapping, Optional

import nox
import tomli as tomllib

PYTHON_VERSIONS: List[str] = ["3.8", "3.9", "3.10", "3.11", "pypy-3.8", "pypy-3.9"]
PYTHON_IMPLEMENTATIONS_SHORT_NAMES: Mapping[str, str] = {"cpython": "py", "pypy": "pypy"}

VERSIONS: MutableMapping[str, Optional[str]] = dict()

with open("pyproject.toml", "rb") as f:
    pyproject_toml = tomllib.load(f)
    VERSIONS.update(pyproject_toml["tool"]["poetry"]["group"]["dev"]["dependencies"])


def _install(session: nox.Session, *dependencies: str) -> None:
    for dependency in dependencies:
        if dependency not in VERSIONS:
            logging.error(f"Dependency {dependency} not found in pyproject.toml")
    session.install(*(f"{dependency}{VERSIONS[dependency]}" for dependency in dependencies))


@nox.session(tags=["checks", "tests"], python=PYTHON_VERSIONS)
def unittests(session: nox.Session) -> None:
    session.install(".")
    _install(session, "pytest")
    session.run("pytest", "tests")


@nox.session(tags=["checks", "tests"])
def doctests(session: nox.Session) -> None:
    session.install(".")
    _install(session, "pytest")
    session.run("pytest", "--doctest-modules", "src")


@nox.session(tags=["checks", "ci", "lint"])
def src_lint(session: nox.Session) -> None:
    session.install(".")
    _install(session, "pylint", "tryceratops")
    session.run("pylint", "src")
    session.run("tryceratops", "src")


@nox.session(tags=["checks", "ci", "lint"])
def docs_lint(session: nox.Session) -> None:
    session.install(".")
    _install(session, "docsig")
    session.run("docsig", "src")


@nox.session(tags=["checks", "ci", "lint"])
def tests_lint(session: nox.Session) -> None:
    session.install(".")
    _install(session, "pylint", "pytest")
    session.run("pylint", "tests")


@nox.session(tags=["checks", "ci", "typecheck"])
def src_typecheck(session: nox.Session) -> None:
    session.install(".")
    _install(session, "mypy")
    session.run("mypy", "--strict", "src")


@nox.session(tags=["checks", "ci", "typecheck"])
def tests_typecheck(session: nox.Session) -> None:
    session.install(".")
    _install(session, "mypy", "pytest")
    session.run("mypy", "--strict", "tests")


@nox.session(tags=["checks", "ci", "fmt"])
def src_fmt(session: nox.Session) -> None:
    _install(session, "isort", "black")
    for formatter in ("isort", "black"):
        session.run(formatter, "--check", "src")


@nox.session(tags=["checks", "ci", "fmt"])
def docs_fmt(session: nox.Session) -> None:
    _install(session, "docformatter", "pydocstyle")
    session.run("pydocstyle", "src")
    session.run("docformatter", "--check", "src")


@nox.session(tags=["checks", "ci", "fmt"])
def tests_fmt(session: nox.Session) -> None:
    _install(session, "isort", "black")
    for formatter in ("isort", "black"):
        session.run(formatter, "--check", "tests")


@nox.session(name="format")
def format_(session: nox.Session) -> None:
    _install(session, "isort", "black", "docformatter")
    for target in ("src", "tests", "noxfile.py"):
        for formatter in ("isort", "black"):
            session.run(formatter, target)

    session.run("docformatter", "--in-place", "src")


@nox.session
def coverage(session: nox.Session) -> None:
    session.install(".")
    _install(session, "coverage", "pytest")
    session.run("coverage", "run", "-m", "pytest")
    session.run("coverage", "report", "--rcfile=pyproject.toml", "-m")
    session.run("coverage", "xml")


@nox.session
def build(session: nox.Session, postfix: Optional[str] = None) -> None:
    python_implementation = platform.python_implementation()
    python_major, python_minor, *_ = sys.version_info
    if postfix is None:
        postfix = (
            f"-{PYTHON_IMPLEMENTATIONS_SHORT_NAMES.get(python_implementation.lower(), 'python')}"
            f"{python_major}"
            f"{python_minor}"
        )
    assert postfix is not None
    _install(session, "shiv")
    session.run(
        "shiv",
        "--console-script",
        "pyggp",
        "--compressed",
        "--output-file",
        f"pyggp{postfix}",
        "--python",
        "/usr/bin/env -S python3 -O",
        ".",
    )
