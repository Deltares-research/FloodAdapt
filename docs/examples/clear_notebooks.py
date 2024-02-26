"""Clear Jupyter output."""

import subprocess
from pathlib import Path

if __name__ == "__main__":
    p = Path(__file__).parent

    # Loop through notebooks
    for nb in p.glob("*ipynb"):
        _file = Path(nb)

        # Execute jupyter clear
        subprocess.call(
            [
                "jupyter",
                "nbconvert",
                "--clear-output",
                "--inplace",
                _file.as_posix(),
            ]
        )
