import os

# The legacy suite talks to a running Anytype Desktop instance and authenticates at
# import time. Keep it available as an opt-in integration suite while allowing the
# deterministic API contract tests to run in CI and local development by default.
collect_ignore = []
if os.environ.get("ANYTYPE_INTEGRATION_TESTS") != "1":
    collect_ignore.extend(["test_anytype.py", "test_issues.py"])
