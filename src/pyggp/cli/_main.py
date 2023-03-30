import typer
from rich import print

import pyggp


def version_callback(value: bool) -> None:
    if value:
        print("[bold]pyggp[/bold] (version %s)" % pyggp.__version__)
        raise typer.Exit
