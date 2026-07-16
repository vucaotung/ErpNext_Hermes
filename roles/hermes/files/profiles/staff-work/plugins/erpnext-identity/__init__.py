"""Registers the /link, /mytasks, and /assign slash commands so Hermes
recognizes them as "known" commands (required for the command:<name>
gateway hook to fire). The actual work happens in the gateway hooks under
~/.hermes/profiles/<profile>/hooks/, which receive the real Telegram
user_id (never available to the LLM) and call the ERPNext API Bridge's
/identity/link, /identity/tasks, /identity/assign_task endpoints directly.

Shared across profiles (ops-admin and staff-work both install this same
plugin) — a profile only actually reacts to a command if it also has the
matching hook directory installed. Without a hook, the command falls
through to the harmless placeholder below (returns None = no reply).
"""


def _link_placeholder(raw_args):
    return None


def _mytasks_placeholder(raw_args):
    return None


def _assign_placeholder(raw_args):
    return None


def register(ctx):
    ctx.register_command(
        "link",
        _link_placeholder,
        description="Liên kết tài khoản Telegram với ERPNext",
        args_hint="<mã>",
    )
    ctx.register_command(
        "mytasks",
        _mytasks_placeholder,
        description="Xem task ERPNext được gán cho bạn",
    )
    ctx.register_command(
        "assign",
        _assign_placeholder,
        description="Giao task cho nhân viên (chỉ Director/Team Lead)",
        args_hint="<task_id> <email>",
    )
