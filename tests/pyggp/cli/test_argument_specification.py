from typing import Mapping, Sequence

import pytest

from pyggp.cli.argument_specification import ArgumentSpecification


@pytest.mark.parametrize(
    ("spec", "expected_name", "expected_args", "expected_kwargs"),
    [
        ("name", "name", (), {}),
        ('name("arg1")', "name", ("arg1",), {}),
        ("name(123)", "name", (123,), {}),
        ('name("arg1", "arg2")', "name", ("arg1", "arg2"), {}),
        ('name(kwarg1="arg1")', "name", (), {"kwarg1": "arg1"}),
        ('name(kwarg1="arg1", kwarg2="arg2")', "name", (), {"kwarg1": "arg1", "kwarg2": "arg2"}),
        ('name("arg1", kwarg1="arg1")', "name", ("arg1",), {"kwarg1": "arg1"}),
        ('name("/path/to/file")', "name", ("/path/to/file",), {}),
        ('name(path="/path/to/file")', "name", (), {"path": "/path/to/file"}),
        ('name(path="123")', "name", (), {"path": "123"}),
        ("module.class", "module.class", (), {}),
        ('module.class("argument")', "module.class", ("argument",), {}),
        ("name('single-quote')", "name", ("single-quote",), {}),
        ("name(True)", "name", (True,), {}),
        ("name(False)", "name", (False,), {}),
        ("name(None)", "name", (None,), {}),
    ],
)
def test_from_str(
    spec: str,
    expected_name: str,
    expected_args: Sequence[str],
    expected_kwargs: Mapping[str, str],
) -> None:
    actual = ArgumentSpecification.from_str(spec)
    expected = ArgumentSpecification(name=expected_name, args=expected_args, kwargs=expected_kwargs)
    assert actual == expected
