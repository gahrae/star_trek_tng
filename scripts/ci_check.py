#!/usr/bin/env python3
"""Run the two steps the deploy workflow runs (build_site.py, check.py) with only what the workflow installs.

.github/workflows/pages.yml does `pip install markdown` and nothing else, so those scripts may import the standard library,
markdown and this project's own modules, and no other package. A package that happens to be installed here (bs4, requests)
would work locally and fail in the deploy, so any other import is refused here with the name of the module.
"""
import sys, runpy, pathlib, importlib.abc
ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
ALLOWED = set(sys.stdlib_module_names) | {"markdown"} | {p.stem for p in SCRIPTS.glob("*.py")}

class OnlyWhatTheWorkflowInstalls(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        top = fullname.split(".")[0]
        if top not in ALLOWED:
            raise ImportError(f"import {fullname!r} is not available in the deploy workflow, which installs only markdown (see .github/workflows/pages.yml)")
        return None

sys.meta_path.insert(0, OnlyWhatTheWorkflowInstalls())
sys.path.insert(0, str(SCRIPTS))
for step in ("build_site.py", "check.py"):
    print(f"== {step} (only markdown available)")
    sys.argv = [step]
    try: runpy.run_path(str(SCRIPTS / step), run_name="__main__")
    except SystemExit as e:
        if e.code not in (None, 0): sys.exit(e.code)
