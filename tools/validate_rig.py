"""Entry point for the current layered character pipeline."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('validate_common_state.py')),run_name="__main__")
