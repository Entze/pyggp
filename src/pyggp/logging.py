import logging
import typer
import rich.logging

handler = rich.logging.RichHandler(
    rich_tracebacks=True,
    markup=True,
)

if not __debug__:
    handler.tracebacks_suppress = [
        typer,
        rich,
    ]

FORMAT = "%(message)s"
logging.basicConfig(
    level=logging.NOTSET,
    format=FORMAT,
    datefmt="[%X]",
    handlers=[handler],
)

log = logging.getLogger("rich")
console_width = rich.get_console().width
log_line_length = console_width - 30
