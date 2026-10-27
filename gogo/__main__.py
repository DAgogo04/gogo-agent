"""Entrypoints — installed as the `gogo` command (and `python -m gogo`):

  gogo                       chat in the terminal (default)
  gogo dashboard             the browser cockpit → localhost:7777 (+ Telegram if configured)
  gogo connections           list configured integrations and their health
  gogo connect google        sign in to Google Calendar (opens your browser)
  gogo connect treg          live data for research, on your own treg account (opens your browser)
  gogo mcp                   MCP servers, and which account each knows you as
  gogo mcp login <name>      sign in again — as someone else, or after expiry
  gogo voice                 talk to it (needs the [voice] extra)
  gogo telegram              phone → laptop (needs TELEGRAM_BOT_TOKEN)
  gogo discord               Discord → laptop (needs DISCORD_BOT_TOKEN)
  gogo whatsapp              WhatsApp → laptop (needs WHATSAPP_TOKEN, public URL)
  gogo brief                 morning briefing (calendar + mail + memory) — as a LOOP
  gogo gather                same job as a GRAPH: github, web, calendar and
                             memory fetched together, then one digest
  gogo skill install <url>   install a third-party skill
  gogo skill export          copy Gogo's skills to Claude Code / Codex (--to claude,codex)
  gogo evals turns           grade your own traced turns with the five turn checks (--window today|7d|all)
"""

from __future__ import annotations

import sys


def _tolerant_stdio() -> None:
    """Windows consoles default to a legacy codepage (cp1252) that cannot
    encode the arrows and middots in our output — printing the dashboard
    banner would crash with UnicodeEncodeError before the server even
    started. Keep the console's encoding but replace what it can't show."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass  # not a real console stream (tests, pipes) — leave it alone


def main() -> None:
    _tolerant_stdio()
    args = sys.argv[1:]
    if not args:
        from gogo.gateway.cli import main as cli_main

        cli_main()
    elif args[0] == "dashboard":
        from gogo.ops.dashboard import main as dash_main

        dash_main()
    elif args[0] == "connections":
        from gogo.integrations import cli_main

        sys.exit(cli_main())
    elif args[0] == "connect":
        from gogo.connect import cli_main as connect_main

        sys.exit(connect_main(args[1:]))
    elif args[0] == "voice":
        from gogo.gateway.voice import main as voice_main

        voice_main()
    elif args[0] == "telegram":
        from gogo.gateway.telegram import main as tg_main

        tg_main()
    elif args[0] == "discord":
        from gogo.gateway.discord import main as discord_main

        discord_main()
    elif args[0] == "whatsapp":
        from gogo.gateway.whatsapp import main as wa_main

        wa_main()
    elif args[0] == "brief":
        from gogo.ops.brief import main as brief_main

        brief_main()
    elif args[0] == "gather":
        from gogo.ops.gather import main as gather_main

        gather_main()
    elif args[0] == "mcp":
        from gogo.tools.mcp_cli import cli_main as mcp_main

        sys.exit(mcp_main())
    elif args[0] == "skill" and len(args) >= 2 and args[1] == "export":
        from gogo.memory.procedural.exporter import cli_main as export_main

        sys.exit(export_main(args[2:]))
    elif args[0] == "evals" and len(args) >= 2 and args[1] == "turns":
        from gogo.ops.turn_evals import cli_main as turns_main

        sys.exit(turns_main(args[2:]))
    elif args[0] == "skill" and len(args) >= 3 and args[1] == "install":
        from gogo.memory.procedural.installer import install

        install(args[2])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
