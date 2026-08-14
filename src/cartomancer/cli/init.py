from pathlib import Path

import typer
from rich.console import Console
from rich.text import Text

console = Console()

_ENV_TEMPLATE = """\
# See .env.example in the Cartomancer repo for the full list of options.
MODELS_DIR=./data/models
DATA_DIR=./data
PROMPTS_DIR=./prompts
COMFYUI_OUTPUT_DIR=./data/comfyui-output
COMFYUI_PORT=8188
"""


def init_command(
    target: Path = typer.Argument(
        Path("."), help="Directory to initialize (default: current directory)."
    ),
) -> None:
    """Scaffold prompts/, data/, and a .env file in a directory. Safe to re-run."""
    target.mkdir(parents=True, exist_ok=True)
    (target / "prompts").mkdir(exist_ok=True)
    (target / "data").mkdir(exist_ok=True)

    env_path = target / ".env"
    if env_path.exists():
        console.print(Text(f"{env_path} already exists, leaving it alone", style="dim"))
    else:
        env_path.write_text(_ENV_TEMPLATE)
        line = Text("created", style="green")
        line.append(f" {env_path}")
        console.print(line)

    ready_line = Text("ready", style="green")
    ready_line.append(f" {target.resolve()}")
    console.print(ready_line)
