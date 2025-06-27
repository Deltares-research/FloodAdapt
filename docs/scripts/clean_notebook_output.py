from pathlib import Path
import os
import shutil
import subprocess


def clean_notebook_output(examples_dir: Path):
    """Clean the output of Jupyter notebooks in the docs directory."""
    notebooks = []

    for root, dirs, files in os.walk(examples_dir):
        for dir in dirs:
            if dir.endswith('.jupyter_cache'):
                shutil.rmtree(os.path.join(root, dir))
                print(f"Removed cache directory: {os.path.join(root, dir)}")
        for file in files:
            path = os.path.join(root, file)
            if file.endswith('.ipynb') and os.path.exists(path):
                subprocess.run(['nbstripout', path], check=True)

if __name__ == "__main__":
    examples_dir = Path(__file__).parent.parent / '3_api_docs' / 'examples'
    clean_notebook_output(examples_dir)
