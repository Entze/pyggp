import logging

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

log: logging.Logger = logging.getLogger("rich")
console_width: int = rich.get_console().width
log_line_length: int = console_width - 30
