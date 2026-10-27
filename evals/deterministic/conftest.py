"""Deterministic eval fixtures are timestamped in UTC; pin the process
timezone so "today" windows resolve identically on every machine."""
from __future__ import annotations

import os
import time

os.environ["TZ"] = "UTC"
if hasattr(time, "tzset"):
    time.tzset()
