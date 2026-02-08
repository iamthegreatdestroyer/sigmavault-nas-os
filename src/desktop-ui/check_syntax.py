"""Syntax-check all Phase 3b files without requiring GTK imports."""

import py_compile
import sys

files = [
    "sigmavault_desktop/utils/formatting.py",
    "sigmavault_desktop/utils/async_helpers.py",
    "sigmavault_desktop/widgets/stat_card.py",
    "sigmavault_desktop/widgets/job_row.py",
    "sigmavault_desktop/views/dashboard_view.py",
    "sigmavault_desktop/views/jobs_view.py",
    "sigmavault_desktop/views/job_detail_view.py",
    "sigmavault_desktop/views/storage_view.py",
    "sigmavault_desktop/views/agents_view.py",
    "sigmavault_desktop/views/system_settings_view.py",
    "sigmavault_desktop/window.py",
    "sigmavault_desktop/app.py",
    "sigmavault_desktop/utils/__init__.py",
    "sigmavault_desktop/widgets/__init__.py",
    "sigmavault_desktop/views/__init__.py",
    "sigmavault_desktop/api/client.py",
    "sigmavault_desktop/api/models.py",
]

passed = 0
failed = 0

for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f"  OK  {f}")
        passed += 1
    except py_compile.PyCompileError as e:
        print(f"  FAIL  {f}")
        print(f"        {e}")
        failed += 1

print(f"\nResults: {passed} passed, {failed} failed out of {len(files)} files")
sys.exit(1 if failed else 0)
