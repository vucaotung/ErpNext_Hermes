"""Registers the /ingest slash command so Hermes recognizes it as a
"known" command (required for the command:ingest gateway hook to fire).
The actual work happens in the gateway hook under
~/.hermes/profiles/<profile>/hooks/ingest-command/, which calls the
onyx-bridge service directly. This plugin only makes the command
routable; without the hook installed too, it falls through to the
placeholder below (returns None = no reply).
"""


def _ingest_placeholder(raw_args):
    return None


def register(ctx):
    ctx.register_command(
        "ingest",
        _ingest_placeholder,
        description="Nạp một URL vào kho tri thức Onyx (pháp chế/dự án)",
        args_hint="<url> [legal|project]",
    )
