"""Compatibility entry point: rebuild the current book without rolling back progress."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('build_book.py')), run_name='__main__')
