"""Presentation-only pseudonyms for benchmark tags.

Apply at export boundaries, including campaign JSON files. Resolve exported
targets against prepared vocabularies before computation. Metrics, ordering and
missing-value buckets are preserved. Pseudonyms are stable across report formats.
"""
from __future__ import annotations

import json
import re

from benchmarks.report_labels import label, legacy_label


FIELDS = {
    "Region", "Device", "Child", "Category", "Channel", "City", "Age", "Gender", "Interest",
    "location", "device", "device_type", "is_child", "category", "content_category",
    "channel", "channel_id", "contractor", "client_version", "place", "position",
    "broadcast", "broadcast_type", "age", "ep", "city", "gender", "interest", "pool_devices",
}
MISSING = {"", "∅", "<other>", "<OTHER>", "::OTHER", "OTHER", "<none>", "<missing>", "None", "none", "nan", "undefined"}
_known: set[str] = set()
_named_pattern = None
_field_pattern = re.compile(
    r"\b(" + "|".join(sorted(map(re.escape, FIELDS), key=len, reverse=True))
    + r")([:=])([^\s,;|\]\[{}()\"'`<>]+)"
)


def tag_label(value, field: str | None = None) -> str | bool:
    """Use readable aliases while preserving missing values and logical flags."""
    if isinstance(value, bool):
        return value
    value = str(value)
    if value in MISSING or re.fullmatch(r"tag_[0-9a-f]{16}", value):
        return value
    return label(value, field)


def register(values) -> None:
    global _named_pattern
    _known.update(str(v) for v in values if str(v) not in MISSING)
    _named_pattern = None


def register_prepared(prep) -> None:
    for values in prep.vocabs.values():
        register(values)


def campaign_config(value):
    """Export campaigns and their metadata with consistent campaign references."""
    ads = value.get("ads", []) if isinstance(value, dict) else value
    for ad in ads:
        register([ad["id"], ad.get("name", ad["id"])])
    return report(value)


def text(value: str) -> str:
    """Sanitize contextual labels without replacing bare numerical metrics."""
    # FullTag and key=value labels, including labels embedded in prose.
    global _named_pattern
    # Time-zone identifiers and time references are metadata, not City tags.
    protected = []
    def protect(match):
        protected.append(match[0])
        return f"PRIVACYTIME{len(protected) - 1}TOKEN"
    value = re.sub(r"Europe/Moscow|Moscow[ -]time", protect, value)
    value = _field_pattern.sub(lambda m: m[0] if m[3] in FIELDS
                               else m[1] + m[2] + tag_label(m[3], m[1]), value)
    # JSON targeting objects often appear inline inside Markdown reports.
    def inline(match):
        try:
            return json.dumps(report(json.loads(match[0])), ensure_ascii=False)
        except (ValueError, TypeError):
            return match[0]
    value = re.sub(r'\{[^{}\n]*\}', inline, value)
    if _known:
        if _named_pattern is None:
            named = [v for v in _known
                     if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", v)
                     and not v.startswith("tag_")
                     and v.lower() not in {"true", "false"} and len(v) > 1]
            pattern = r"(?<![\w])(" + "|".join(sorted(map(re.escape, named), key=len, reverse=True)) + r")(?![\w])"
            _named_pattern = re.compile(pattern) if named else False
        if _named_pattern:
            value = _named_pattern.sub(lambda m: tag_label(m[0]), value)
        # A quoted/backticked number is a label; a bare number can be a metric.
        value = re.sub(r"([`\"'])(\d+)\1", lambda m: m[1] + tag_label(m[2]) + m[1]
                       if m[2] in _known else m[0], value)
    for i, original in enumerate(protected):
        value = value.replace(f"PRIVACYTIME{i}TOKEN", original)
    return value


def report(value, field: str | None = None):
    """Return a sanitized copy; never mutate the computation's dictionaries."""
    if field in FIELDS:
        if isinstance(value, list):
            return [tag_label(v, field) for v in value]
        if isinstance(value, dict):
            return {tag_label(k, field): report(v) for k, v in value.items()}
        return tag_label(value, field)
    if isinstance(value, dict):
        slice_field = value.get("field", value.get("tag"))
        change_field = value.get("vocab")
        campaign = "id" in value and ("targets" in value or "cpm" in value)
        return {k: (tag_label(v, slice_field) if k == "value" and slice_field in FIELDS
                    else tag_label(v, change_field) if k == "tag" and change_field in FIELDS
                    else tag_label(v, "Campaign") if campaign and k in {"id", "name"}
                    else report(v, k)) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [report(v, field) for v in value]
    return text(value) if isinstance(value, str) else value


def markdown(value: str) -> str:
    """Sanitize categorical table cells as well as inline targeting expressions."""
    lines, headers = [], []
    for line in value.splitlines(keepends=True):
        if line.lstrip().startswith("|"):
            cells = line.strip().strip("|").split("|")
            names = [c.strip().strip("`") for c in cells]
            header_names = [{"Cut": "field", "Field": "field", "Tag": "tag", "Value": "value"}.get(n, n)
                            for n in names]
            if not headers:
                headers = header_names
            elif headers and not all(re.fullmatch(r"[:\-\s]*", c) for c in cells):
                row_field = next((names[i] for i, h in enumerate(headers)
                                  if h in {"field", "tag"} and i < len(names)), None)
                for i, h in enumerate(headers):
                    if i < len(cells) and (h in FIELDS or h == "value" and row_field in FIELDS
                                          or h in {"Ad", "Campaign", "Company", "Name", "id"}):
                        cells[i] = " " + tag_label(names[i], row_field if h == "value" else h) + " "
                line = "|" + "|".join(cells) + "|" + ("\n" if line.endswith("\n") else "")
        else:
            headers = []
        lines.append(text(line))
    return "".join(lines)


def dataframe(frame):
    """Sanitize an EDA table copy, retaining all numerical measure columns."""
    result = frame.copy()
    for column in result.columns:
        if column in FIELDS:
            result[column] = result[column].map(lambda v: tag_label(v, column))
        elif str(column) == "value" and "tag" in result:
            result[column] = [tag_label(v, t) if t in FIELDS else v
                              for t, v in zip(result["tag"], result[column])]
        elif result[column].dtype == object:
            result[column] = result[column].map(lambda v: text(v) if isinstance(v, str) else v)
    if result.index.name in FIELDS:
        result.index = result.index.map(lambda v: tag_label(v, result.index.name))
    result.columns = [tag_label(c) if str(c) in _known and c not in FIELDS else text(str(c))
                      for c in result.columns]
    return result


def figure(fig) -> None:
    from matplotlib.text import Text
    from matplotlib.ticker import FixedLocator
    # Materialize tick labels before replacing their text.
    fig.canvas.draw()
    for axes in fig.axes:
        for axis, labels, ticks, setter in (
                (axes.xaxis, axes.get_xticklabels(), axes.get_xticks(), axes.set_xticks),
                (axes.yaxis, axes.get_yticklabels(), axes.get_yticks(), axes.set_yticks)):
            strings = [label.get_text() for label in labels]
            categorical = (isinstance(axis.get_major_locator(), FixedLocator) and bool(strings)
                           and all(s in _known or s in MISSING for s in strings))
            safe = [tag_label(s) if s in _known and
                    (not s.replace(".", "", 1).isdigit()
                     or categorical and s.isdigit() and int(s) > 10000)
                    else text(s) for s in strings]
            if safe != strings:
                setter(ticks, safe)
    for artist in fig.findobj(match=Text):
        label = artist.get_text()
        # Automatic numeric ticks describe measured quantities, not tag IDs.
        categorical = label in _known and not label.replace(".", "", 1).isdigit()
        artist.set_text(tag_label(label) if categorical else text(label))
