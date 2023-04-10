import platform
import sys

import rich.live as rich_live
import typer

import pyggp


def version_callback(value: bool) -> None:
    if value:
        pyggp_major_version, pyggp_minor_version, pyggp_patch_version = pyggp.__version__.split(".")
        with rich_live.Live() as live:
            live.console.print(
                "[bold]pyggp[/bold] (version [cyan]%s[/cyan].[cyan]%s[/cyan].[cyan]%s[/cyan])"
                % (pyggp_major_version, pyggp_minor_version, pyggp_patch_version),
                highlight=False,
            )

        raise typer.Exit


def sys_info_callback(value: bool) -> None:
    if value:
        pyggp_major_version, pyggp_minor_version, pyggp_patch_version = pyggp.__version__.split(".")
        python_major_version, python_minor_version, python_patch_version = sys.version_info[:3]
        platform_name = platform.system()
        platform_version = platform.release()
        with rich_live.Live() as live:
            live.console.print(
                "[bold]pyggp[/bold] (version [cyan]%s[/cyan].[cyan]%s[/cyan].[cyan]%s[/cyan])"
                % (pyggp_major_version, pyggp_minor_version, pyggp_patch_version),
                highlight=False,
            )
            live.console.print(
                "[bold]Python[/bold] (version [cyan]%d[/cyan].[cyan]%d[/cyan].[cyan]%d[/cyan])"
                % (python_major_version, python_minor_version, python_patch_version),
                highlight=False,
            )
            live.console.print(
                "[bold]Platform[/bold] ([green]%s[/green]-[cyan]%s[/cyan])" % (platform_name, platform_version),
                highlight=False,
            )
        raise typer.Exit
