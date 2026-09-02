import inspect
from pathlib import Path

def print_link(file_path: Path):
    print(f"file:///{file_path.__str__()}".replace('\\', '/'))
