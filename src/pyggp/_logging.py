import logging

import inflection
import rich.logging
import typer

handler: rich.logging.RichHandler = rich.logging.RichHandler(
    rich_tracebacks=True,
    markup=True,
)

if not __debug__:
    handler.tracebacks_suppress = [
        typer,
        rich,
    ]

FORMAT: str = "%(message)s"
logging.basicConfig(
    level=logging.NOTSET,
    format=FORMAT,
    datefmt="[%X]",
    handlers=[handler],
)

log: logging.Logger = logging.getLogger("pyggp")


def inflect(noun: str, count: int = 0, with_count: bool = True) -> str:
    if count == 1:
        noun_ = inflection.singularize(noun)
    else:
        noun_ = inflection.pluralize(noun)
    if with_count:
        count_str = f"{count} "
    else:
        count_str = ""
    return f"{count_str}{noun_}"
