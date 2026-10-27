"""Entry point for the current layered character pipeline."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('unified_rig.py')),run_name="__main__")
