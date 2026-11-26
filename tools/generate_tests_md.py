#!/usr/bin/env python3
"""
Generates extended markdown from fixtures/cases/*.json.

Usage (from project root):
    python -m tools.generate_tests_md                            # default paths
    python -m tools.generate_tests_md path/to/fixtures/cases/    # custom cases dir
    python -m tools.generate_tests_md cases_dir output.md        # explicit output
"""

import inspect
import json
import sys
from pathlib import Path

from rtb_sdk.helpers import create_ad
from tests.auction._functions import FUNCTIONS
from rtb_sdk.constants import DATE_ZERO, DATE_INFINITY, INT_INFINITY

AD_KEYS = set(create_ad().keys())


# ---------------------------------------------------------------------------
# Function metadata via inspect
# ---------------------------------------------------------------------------

def get_signature(func_name: str, func) -> str:
    """
    Extract the full signature from source, collapsing multi-line defs into one line.
    Preserves short type names as written in the source.
    """
    try:
        src = inspect.getsource(func)
        lines = src.splitlines()
        # Find the 'def' line and collect until the closing '):'
        collecting = False
        parts: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("def "):
                collecting = True
            if collecting:
                parts.append(stripped)
                # Stop when we see the closing paren + colon of the signature
                joined = " ".join(parts)
                if "):" in joined or ") ->" in joined and joined.rstrip().endswith(":"):
                    break
        if parts:
            sig = " ".join(parts).rstrip(":")
            # Collapse trailing comma before closing paren: (a, b, ) -> (a, b)
            sig = sig.replace(", )", ")").replace(",)", ")")
            return sig
    except Exception:
        pass
    try:
        return f"def {func_name}{inspect.signature(func)}"
    except Exception:
        return f"def {func_name}(...)"


def get_description(func) -> str:
    doc = inspect.getdoc(func) or ""
    return doc.split("\n")[0].strip() if doc else ""


# ---------------------------------------------------------------------------
# file:// helpers
# ---------------------------------------------------------------------------

def is_file_ref(val) -> bool:
    return isinstance(val, str) and val.startswith("file://")


def collect_file_refs(val) -> set:
    """Recursively collect all fixture paths referenced via 'file://path'."""
    refs: set = set()
    if val is None:
        return refs
    if is_file_ref(val):
        refs.add(val[len("file://"):])
    elif isinstance(val, dict):
        for v in val.values():
            refs |= collect_file_refs(v)
    elif isinstance(val, list):
        for v in val:
            refs |= collect_file_refs(v)
    return refs


def expand_ads_dict_refs(refs: set, tests_dir: Path) -> set:
    """
    For each ads_dict fixture in refs, open the file and collect the
    nested file:// references (the individual ad files inside the dict).
    Returns expanded set containing both the dict ref and every ad ref.
    """
    expanded = set(refs)
    for ref in refs:
        if "ads_dict" not in ref:
            continue
        fixture_path = tests_dir / ref
        if not fixture_path.exists():
            continue
        try:
            with open(fixture_path, encoding="utf-8") as fh:
                data = json.load(fh)
            expanded |= collect_file_refs(data)
        except Exception:
            pass
    return expanded


def file_link(path: str) -> str:
    name = Path(path).stem
    return f"[{name}]({path})"


def file_refs_line(refs: set) -> str:
    links = ", ".join(file_link(r) for r in sorted(refs))
    return f"_Fixtures: {links}_"


# ---------------------------------------------------------------------------
# Value formatting
# ---------------------------------------------------------------------------

def py_repr(val, depth=0) -> str:
    pad = "    " * depth
    inner = "    " * (depth + 1)

    if val is None:
        return "None"
    if is_file_ref(val):
        return Path(val[len("file://"):]).stem
    if isinstance(val, bool):
        return "True" if val else "False"
    if isinstance(val, str):
        if val == DATE_ZERO:
            return "DATE_ZERO"
        if val == DATE_INFINITY:
            return "DATE_INFINITY"
        return repr(val)
    if isinstance(val, int):
        if val == INT_INFINITY:
            return "INT_INFINITY"
        return str(val)
    if isinstance(val, float):
        return repr(val)
    if isinstance(val, list):
        if not val:
            return "[]"
        return "[" + ", ".join(py_repr(v, depth) for v in val) + "]"
    if isinstance(val, dict):
        if not val:
            return "{}"
        pairs = [f"{inner}{repr(k)}: {py_repr(v, depth + 1)}," for k, v in val.items()]
        return "{\n" + "\n".join(pairs) + "\n" + pad + "}"
    return repr(val)


def is_ad(d) -> bool:
    return isinstance(d, dict) and len(AD_KEYS & d.keys()) >= 4


def _format_ad_block(label: str, ad_val: dict) -> str:
    lines = [f"{label} = {{"]
    for k, v in ad_val.items():
        lines.append(f"    {repr(k)}: {py_repr(v, 1)},")
    lines.append("}")
    return "\n".join(lines)


def format_input(inp: dict) -> str:
    lines = []
    for key, val in inp.items():
        if key == "ads" and isinstance(val, dict) and not is_file_ref(val):
            if not val:
                lines.append(f"{key} = {{}}")
            else:
                lines.append(f"{key} = {{")
                for ad_id, ad_val in val.items():
                    lines.append(f"    {repr(ad_id)}: {py_repr(ad_val, 1)},")
                lines.append("}")
        else:
            lines.append(f"{key} = {py_repr(val)}")
    return "\n".join(lines)


def format_output(case: dict) -> tuple[str, str]:
    error = case.get("error")
    output = case.get("output")
    check_output_type = case.get("check_output_type")
    description = case.get("description", "")

    if error:
        return "", f"raises {error}"

    if output is None:
        if check_output_type:
            return "python", f"# Non-deterministic — return Ad-facility\n# {description}"
        return "", "None"

    if is_file_ref(output):
        return "", file_link(output[len("file://"):])

    if isinstance(output, bool):
        return "", "True" if output else "False"
    if isinstance(output, (int, float)):
        return "", py_repr(output)
    if isinstance(output, str):
        return "", repr(output)
    if isinstance(output, dict):
        if is_ad(output):
            return "python", _format_ad_block("result", output)
        return "python", py_repr(output)

    return "", repr(output)


def case_title(i: int, case: dict) -> str:
    title = f"case{i + 1}"
    if case.get("error"):
        title += " (error)"
    elif case.get("check_output_type"):
        title += " (non-deterministic)"
    return title


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def render_toc(func_names: list[str]) -> str:
    lines = ["## Contents", ""]
    for name in func_names:
        anchor = name.lower()
        lines.append(f"- [{name}](#{anchor})")
    lines.append("")
    return "\n".join(lines)


def render_function(func_name: str, func, cases: list[dict], tests_dir: Path) -> str:
    out = []

    description = get_description(func)
    signature = get_signature(func_name, func)

    out.append(f"# {func_name}")
    out.append("")

    if description:
        out.append(f"> {description}")
        out.append("")

    out.append("```python")
    out.append(signature)
    out.append("```")
    out.append("")

    for i, case in enumerate(cases):
        title = case.get("description", case_title(i, case))
        inp = case.get("input", {})
        output_val = case.get("output")

        out.append(f"{title}:")
        out.append("")

        raw_refs = collect_file_refs(inp) | collect_file_refs(output_val)
        case_file_refs = expand_ads_dict_refs(raw_refs, tests_dir)
        if case_file_refs:
            out.append(file_refs_line(case_file_refs))
            out.append("")

        out.append("input:")
        out.append("```python")
        out.append(format_input(inp))
        out.append("```")

        lang, out_str = format_output(case)
        out.append("output:")
        out.append(f"```{lang}")
        out.append(out_str)
        out.append("```")
        out.append("")

    return "\n".join(out)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    cases_dir = Path(args[0]) if args else Path("tests/auction/cases")
    output_path = (
        Path(args[1]) if len(args) > 1
        else cases_dir.parent / "tests.md"
    )
    # tests_dir — the base for resolving file:// links inside the cases
    tests_dir = cases_dir.parent

    func_names = list(FUNCTIONS.keys())
    toc = render_toc(func_names)

    sections = []
    total_cases = 0
    missing = []

    for func_name, func in FUNCTIONS.items():
        case_file = cases_dir / f"{func_name}.json"
        if not case_file.exists():
            missing.append(func_name)
            continue
        with open(case_file, encoding="utf-8") as f:
            cases_list = json.load(f)
        total_cases += len(cases_list)
        sections.append(render_function(func_name, func, cases_list, tests_dir))

    content = toc + "\n---\n\n" + "\n---\n\n".join(sections)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content + "\n")

    print(
        f"Generated {output_path}  "
        f"({len(sections)} functions, {total_cases} cases)"
    )
    if missing:
        print(f"WARNING: no case file for: {', '.join(missing)}")


if __name__ == "__main__":
    main()
