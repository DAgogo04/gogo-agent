"""Shared env-stripping helper for delegate subprocesses.

pi (via delegate_task) and autorun (via workspace.autorun) both spawn
subprocesses that can read the full parent environment. A host application
that holds a secret the delegate has no business seeing can name it via
GOGO_DELEGATE_ENV_DENY (comma-separated) to have it stripped from every
delegated subprocess.
"""

from __future__ import annotations

import os

_DELEGATE_ENV_DENY_VAR = "GOGO_DELEGATE_ENV_DENY"


def delegate_env_denylist() -> frozenset:
    """Names of env vars to strip, read from GOGO_DELEGATE_ENV_DENY.

    Read at call time rather than import time, so a host application can set
    the policy after importing gogo, and so the value cannot go stale in a
    long-running process.

    Note: env var names are matched exactly (case-sensitive) against the keys
    in os.environ. On Windows, environment variable names are case-insensitive
    at the OS level, but dict operations on the copy returned by
    delegate_env() are case-sensitive. Callers on Windows should ensure the
    names in GOGO_DELEGATE_ENV_DENY match the casing used by the host
    application when setting the variable.
    """
    raw = os.getenv(_DELEGATE_ENV_DENY_VAR, "")
    return frozenset(name.strip() for name in raw.split(",") if name.strip())


def delegate_env() -> dict[str, str]:
    """Return a copy of os.environ with delegate-dangerous vars stripped.

    GOGO_DELEGATE_ENV_DENY itself is deliberately NOT stripped: propagating it
    means a nested gogo invocation inside the delegate inherits the same
    policy instead of silently losing it.
    """
    env = os.environ.copy()
    for key in delegate_env_denylist():
        env.pop(key, None)
    return env
