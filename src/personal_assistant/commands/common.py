"""Commands that belong to no entity: help, exit and the web interface."""

from __future__ import annotations

from typing import Annotated

import typer

from personal_assistant import ui
from personal_assistant.errors import ExitLoop


def register(app: typer.Typer) -> None:
    """Add the global commands to the command tree."""

    @app.command("help")
    def show_help(
        topic: Annotated[
            list[str] | None,
            typer.Argument(
                metavar="<command>...",
                help="the command to explain, for example 'help contact add'",
            ),
        ] = None,
    ) -> None:
        """show the available commands"""
        # Reached only in the interactive session, where `--help` is awkward to
        # type; the dispatcher turns the topic into that flag.
        raise ShowHelp(tuple(topic or ()))

    @app.command("exit")
    def leave() -> None:
        """leave the interactive session"""
        raise ExitLoop

    @app.command("quit", hidden=True)
    def leave_quit() -> None:
        """leave the interactive session"""
        raise ExitLoop

    @app.command("close", hidden=True)
    def leave_close() -> None:
        """leave the interactive session"""
        raise ExitLoop

    @app.command("web")
    def start_web(ctx: typer.Context) -> None:
        """start the web interface"""
        import webbrowser

        from personal_assistant.web.app import create_app

        host, port = "127.0.0.1", 5050
        url = f"http://{host}:{port}/"
        ui.success(f"Serving on {url} — press Ctrl-C to return to the assistant.")
        webbrowser.open(url)
        try:
            create_app(ctx.obj).run(host=host, port=port, debug=False)
        except KeyboardInterrupt:
            ui.render("Stopped the web interface.")


class ShowHelp(Exception):
    """Asks the dispatcher to print the help of a command.

    Typer renders help while parsing, so a `help` command cannot print it
    itself; it reports which command was asked about and the dispatcher runs
    that command again with `--help`.
    """

    def __init__(self, topic: tuple[str, ...]) -> None:
        super().__init__(" ".join(topic))
        self.topic = topic
