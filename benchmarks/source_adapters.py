"""Optional source integration, kept outside the versioned benchmark code."""
from __future__ import annotations

import json
import os
from pathlib import Path
import runpy


def adapter_directory() -> Path:
    return Path(os.environ.get("AUCTION_SOURCE_ADAPTERS",
                               Path(__file__).resolve().parents[1] / ".local/source_adapters"))


def _read_aliases(filename: str) -> dict[str, str]:
    path = adapter_directory() / filename
    if not path.exists():
        return {}
    aliases = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(aliases, dict) or not all(isinstance(k, str) and isinstance(v, str)
                                               for k, v in aliases.items()):
        raise ValueError(f"Expected a mapping of source names to public aliases: {path}")
    return aliases


def device_aliases() -> dict[str, str]:
    return _read_aliases("device_aliases.json")


def label_aliases() -> dict[str, str]:
    return _read_aliases("label_aliases.json")


def run_adapter(name: str) -> None:
    path = adapter_directory() / f"{name}.py"
    if not path.is_file():
        raise SystemExit("Local source adapter is unavailable. See docs/local_sources.md; "
                         "public examples use examples.sample_data instead.")
    runpy.run_path(str(path), run_name="__main__")
