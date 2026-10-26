"""Allow `python -m lume.cli` for scheduler-generated commands."""
from lume.cli.main import app

if __name__ == "__main__":
    app()
