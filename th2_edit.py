#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


DECLARATION_PREFIXES = ("scrap", "line", "point", "area")
SECTION_SCRAP_RE = re.compile(
    r'^(?P<indent>\s*)point\s+(?P<x>\S+)\s+(?P<y>\S+)\s+section\b.*\s-scrap\s+(?P<scrap>\S+)'
)
STATION_POINT_RE = re.compile(
    r'^(?P<indent>\s*)point\s+(?P<x>\S+)\s+(?P<y>\S+)\s+station\b.*\s-name\s+(?P<name>\[[^\]]*\]|"[^"]*"|\S+)'
)
EXTEND_LEFT_RE = re.compile(r"^\s*extend\s+left\s*(?:#.*)?$")
NORMAL_SHOT_RE = re.compile(r"^(?P<indent>\s*)(?P<from>[^\s#]+)\s+(?P<to>[^\s#]+)\s+\S+\s+\S+\s+\S+\s*(?:#.*)?$")


@dataclass
class EditResult:
    text: str
    changed: int


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return stream.read()


def write_text(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        stream.write(text)


def _split_line_ending(line: str) -> tuple[str, str]:
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n") or line.endswith("\r"):
        return line[:-1], line[-1]
    return line, ""


def _line_ending(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def replace_text(text: str, find: str, repl: str, regex: bool, count: int = 0) -> EditResult:
    if regex:
        new_text, changed = re.subn(find, repl, text, count=count)
        return EditResult(new_text, changed)

    changed = text.count(find) if count == 0 else min(text.count(find), count)
    new_text = text.replace(find, repl, count if count != 0 else -1)
    return EditResult(new_text, changed)


def _line_is_declaration(line: str) -> bool:
    stripped = line.lstrip()
    if not stripped or stripped.startswith("#"):
        return False
    return stripped.startswith(DECLARATION_PREFIXES)


def _option_pattern(option: str) -> re.Pattern[str]:
    escaped = re.escape(option)
    # Match one Therion option value as bracketed list, quoted string, or bare token.
    return re.compile(rf"(?P<lead>^|\s)-{escaped}(?P<gap>\s+)(?P<value>\[[^\]]*\]|\"[^\"]*\"|\S+)")


def set_option(text: str, match_regex: str, option: str, value: str) -> EditResult:
    matcher = re.compile(match_regex)
    option_re = _option_pattern(option)

    changed = 0
    out_lines: list[str] = []

    for line in text.splitlines(keepends=True):
        body, nl = _split_line_ending(line)

        if _line_is_declaration(body) and matcher.search(body):
            if option_re.search(body):
                replacement = r"\g<lead>-{} {}".format(option, value)
                updated = option_re.sub(replacement, body, count=1)
            else:
                updated = f"{body} -{option} {value}"
            if updated != body:
                changed += 1
            out_lines.append(updated + nl)
            continue

        out_lines.append(line)

    return EditResult("".join(out_lines), changed)


def delete_option(text: str, match_regex: str, option: str) -> EditResult:
    matcher = re.compile(match_regex)
    option_re = _option_pattern(option)

    changed = 0
    out_lines: list[str] = []

    for line in text.splitlines(keepends=True):
        body, nl = _split_line_ending(line)

        if _line_is_declaration(body) and matcher.search(body):
            updated = option_re.sub("", body, count=1)
            updated = re.sub(r"\s{2,}", " ", updated).rstrip()
            if updated != body:
                changed += 1
            out_lines.append(updated + nl)
            continue

        out_lines.append(line)

    return EditResult("".join(out_lines), changed)


def convert_pit_to_floor_step(text: str) -> EditResult:
    changed = 0
    out_lines: list[str] = []
    pit_re = re.compile(r"^(\s*line\s+)pit(\b)(.*)$")

    for line in text.splitlines(keepends=True):
        body, nl = _split_line_ending(line)
        match = pit_re.match(body)
        if match is None:
            out_lines.append(line)
            continue

        updated = f"{match.group(1)}floor-step{match.group(3)}"
        if updated != body:
            changed += 1
        out_lines.append(updated + nl)

    return EditResult("".join(out_lines), changed)


def convert_chimney_to_ceiling_step(text: str) -> EditResult:
    changed = 0
    out_lines: list[str] = []
    chimney_re = re.compile(r"^(\s*line\s+)chimney(\b)(.*)$")
    reverse_re = _option_pattern("reverse")

    for line in text.splitlines(keepends=True):
        body, nl = _split_line_ending(line)
        match = chimney_re.match(body)
        if match is None:
            out_lines.append(line)
            continue

        updated = f"{match.group(1)}ceiling-step{match.group(3)}"
        if reverse_re.search(updated):
            updated = reverse_re.sub(r"\g<lead>-reverse on", updated, count=1)
        else:
            updated = f"{updated} -reverse on"

        if updated != body:
            changed += 1
        out_lines.append(updated + nl)

    return EditResult("".join(out_lines), changed)


def convert_rock_border_close_on(text: str) -> EditResult:
    changed = 0
    out_lines: list[str] = []
    rock_border_re = re.compile(r"^(\s*line\s+)rock-border(\b)(.*)$")
    close_re = _option_pattern("close")

    for line in text.splitlines(keepends=True):
        body, nl = _split_line_ending(line)
        match = rock_border_re.match(body)
        if match is None:
            out_lines.append(line)
            continue

        updated = body
        if close_re.search(updated):
            updated = close_re.sub(r"\g<lead>-close on", updated, count=1)
        else:
            updated = f"{updated} -close on"

        if updated != body:
            changed += 1
        out_lines.append(updated + nl)

    return EditResult("".join(out_lines), changed)


def _strip_quoted_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        return value[1:-1].strip()
    return value


def _extract_station_name_from_scrap(scrap_name: str) -> str | None:
    station_name = scrap_name.rsplit("-", 1)[-1].strip()
    return station_name or None


def _find_previous_nonempty_line(lines: list[str], start_index: int) -> int | None:
    for index in range(start_index, -1, -1):
        if lines[index].strip():
            return index
    return None


def _has_adjacent_section_line(lines: list[str], station_index: int) -> bool:
    previous_index = _find_previous_nonempty_line(lines, station_index - 1)
    if previous_index is None or lines[previous_index].strip() != "endline":
        return False

    for index in range(previous_index - 1, -1, -1):
        stripped = lines[index].strip()
        if not stripped:
            continue
        if stripped.startswith("line section "):
            return "-direction both" in stripped
        if _line_is_declaration(stripped):
            return False

    return False


def _format_decimal(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _offset_coordinate(value: str, delta: str) -> str:
    return _format_decimal(Decimal(value) + Decimal(delta))


def _detect_indentation(lines: list[str]) -> str:
    indentation_counts: dict[str, int] = {}

    for line in lines:
        match = re.match(r"^(\s+)(?=\S)", line)
        if match is not None:
            indentation = match.group(1)
            indentation_counts[indentation] = indentation_counts.get(indentation, 0) + 1

    if not indentation_counts:
        return "  "

    return max(indentation_counts, key=indentation_counts.get)


def _build_section_line(
    indent: str, child_indent: str, station_x: str, station_y: str, newline: str
) -> list[str]:
    start_x = _offset_coordinate(station_x, "-10")
    start_y = _offset_coordinate(station_y, "10")
    end_x = _offset_coordinate(station_x, "10")
    end_y = _offset_coordinate(station_y, "-10")

    return [
        f"{indent}line section -direction both{newline}",
        f"{indent}{child_indent}{start_x} {start_y}{newline}",
        f"{indent}{child_indent}{end_x} {end_y}{newline}",
        f"{indent}{child_indent}smooth off{newline}",
        f"{indent}endline{newline}",
        newline,
    ]


def add_section_lines_for_scraps(text: str) -> EditResult:
    lines = text.splitlines(keepends=True)
    child_indent = _detect_indentation(lines)
    newline = _line_ending(text)
    station_points: dict[str, tuple[int, str, str, str]] = {}
    pending_station_names: set[str] = set()

    for index, line in enumerate(lines):
        section_match = SECTION_SCRAP_RE.match(line.rstrip("\n"))
        if section_match is not None:
            station_name = _extract_station_name_from_scrap(section_match.group("scrap"))
            if station_name:
                pending_station_names.add(station_name)
            continue

        station_match = STATION_POINT_RE.match(line.rstrip("\n"))
        if station_match is None:
            continue

        station_points[_strip_quoted_value(station_match.group("name"))] = (
            index,
            station_match.group("indent"),
            station_match.group("x"),
            station_match.group("y"),
        )

    insertions: list[tuple[int, list[str]]] = []
    for station_name in pending_station_names:
        station_point = station_points.get(station_name)
        if station_point is None:
            continue

        station_index, indent, station_x, station_y = station_point
        if _has_adjacent_section_line(lines, station_index):
            continue

        insertions.append(
            (
                station_index,
                _build_section_line(indent, child_indent, station_x, station_y, newline),
            )
        )

    if not insertions:
        return EditResult(text, 0)

    changed = 0
    for station_index, block in sorted(insertions, key=lambda item: item[0], reverse=True):
        lines[station_index:station_index] = block
        changed += 1

    return EditResult("".join(lines), changed)


def mark_backsights_as_duplicate(text: str) -> EditResult:
    lines = text.splitlines(keepends=True)
    newline = _line_ending(text)
    changed = 0
    out_lines: list[str] = []
    after_extend_left = False
    already_duplicate = False

    for line in lines:
        body, _ = _split_line_ending(line)

        if EXTEND_LEFT_RE.match(body):
            after_extend_left = True
            already_duplicate = False
            out_lines.append(line)
            continue

        if not after_extend_left:
            out_lines.append(line)
            continue

        stripped = body.strip()
        if not stripped or stripped.startswith("#"):
            out_lines.append(line)
            continue

        if stripped == "flags duplicate":
            already_duplicate = True
            out_lines.append(line)
            continue

        if stripped.startswith("flags "):
            out_lines.append(line)
            continue

        after_extend_left = False
        shot_match = NORMAL_SHOT_RE.match(body)
        if (
            already_duplicate
            or shot_match is None
            or shot_match.group("from") == "-"
            or shot_match.group("to") == "-"
        ):
            out_lines.append(line)
            continue

        indent = shot_match.group("indent")
        out_lines.extend((f"{indent}flags duplicate{newline}", line, f"{indent}flags not duplicate{newline}"))
        changed += 1

    return EditResult("".join(out_lines), changed)


def convert_all_default_types(text: str) -> EditResult:
    pit_result = convert_pit_to_floor_step(text)
    chimney_result = convert_chimney_to_ceiling_step(pit_result.text)
    rock_border_result = convert_rock_border_close_on(chimney_result.text)
    section_result = add_section_lines_for_scraps(rock_border_result.text)
    return EditResult(
        section_result.text,
        pit_result.changed + chimney_result.changed + rock_border_result.changed + section_result.changed,
    )


def apply_output(path: Path, result: EditResult, in_place: bool, output: Path | None, backup: bool) -> None:
    if in_place and result.changed == 0:
        return

    if in_place:
        if backup:
            backup_path = path.with_suffix(path.suffix + ".bak")
            write_text(backup_path, read_text(path))
        write_text(path, result.text)
        return

    if output is not None:
        write_text(output, result.text)
        return

    sys.stdout.write(result.text)


def edit_file(path: Path, args: argparse.Namespace, parser: argparse.ArgumentParser) -> EditResult:
    text = read_text(path)

    if path.suffix.lower() == ".th":
        result = EditResult(text, 0)
        if args.mark_backsights:
            result = mark_backsights_as_duplicate(text)
    elif args.command == "replace":
        result = replace_text(text, args.find, args.replace, args.regex, args.count)
    elif args.command == "set-option":
        result = set_option(text, args.match, args.option, args.value)
    elif args.command == "delete-option":
        result = delete_option(text, args.match, args.option)
    elif args.command == "pit-to-floor-step":
        result = convert_pit_to_floor_step(text)
    elif args.command == "chimney-to-ceiling-step":
        result = convert_chimney_to_ceiling_step(text)
    elif args.command == "rock-border-close-on":
        result = convert_rock_border_close_on(text)
    elif args.command == "all-conversions":
        result = convert_all_default_types(text)
    else:
        parser.error(f"Unsupported command: {args.command}")

    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Modify Therion .th and .th2 files")

    parser.add_argument("file", type=Path, help="Input .th or .th2 file, or a directory containing them")
    parser.add_argument("--in-place", action="store_true", help="Write edits back to input file")
    parser.add_argument("--output", type=Path, help="Write edited content to this output file")
    parser.add_argument("--no-backup", action="store_true", help="Disable .bak file when using --in-place")
    backsight_group = parser.add_mutually_exclusive_group()
    backsight_group.add_argument(
        "--mark-backsights",
        dest="mark_backsights",
        action="store_true",
        help="Mark backsights after 'extend left' as duplicate in .th files (default)",
    )
    backsight_group.add_argument(
        "--no-mark-backsights",
        dest="mark_backsights",
        action="store_false",
        help="Do not mark backsights as duplicate in .th files",
    )
    parser.set_defaults(mark_backsights=True)

    sub = parser.add_subparsers(dest="command", required=False)
    parser.set_defaults(command="all-conversions")

    replace = sub.add_parser("replace", help="Find and replace text")
    replace.add_argument("--find", required=True, help="Text or regex to find")
    replace.add_argument("--replace", required=True, help="Replacement text")
    replace.add_argument("--regex", action="store_true", help="Treat --find as regex")
    replace.add_argument("--count", type=int, default=0, help="Maximum replacements (0 means all)")

    set_opt = sub.add_parser("set-option", help="Set or append an option on matching declaration lines")
    set_opt.add_argument("--match", required=True, help="Regex used to select lines to edit")
    set_opt.add_argument("--option", required=True, help="Option name without leading dash")
    set_opt.add_argument("--value", required=True, help="New option value")

    del_opt = sub.add_parser("delete-option", help="Delete an option from matching declaration lines")
    del_opt.add_argument("--match", required=True, help="Regex used to select lines to edit")
    del_opt.add_argument("--option", required=True, help="Option name without leading dash")

    sub.add_parser(
        "pit-to-floor-step",
        help="Convert all 'line pit' declarations to 'line floor-step'",
    )

    sub.add_parser(
        "chimney-to-ceiling-step",
        help="Convert all 'line chimney' declarations to 'line ceiling-step -reverse on'",
    )

    sub.add_parser(
        "rock-border-close-on",
        help="Convert all 'line rock-border' declarations to include '-close on'",
    )

    sub.add_parser(
        "all-conversions",
        help="Apply all default conversions (pit, chimney, rock-border, and section lines)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.in_place and args.output is not None:
        parser.error("Use either --in-place or --output, not both.")

    input_path: Path = args.file
    if not input_path.exists():
        parser.error(f"Input path not found: {input_path}")

    if input_path.is_dir():
        if args.output is not None:
            parser.error("--output cannot be used when the input path is a directory.")
        input_paths = sorted(
            path for path in input_path.iterdir() if path.is_file() and path.suffix.lower() in {".th", ".th2"}
        )
        in_place = True
        backup = False
    else:
        input_paths = [input_path]
        in_place = args.in_place
        backup = not args.no_backup

    for path in input_paths:
        result = edit_file(path, args, parser)
        apply_output(path, result, in_place, args.output, backup=backup)
        if input_path.is_dir():
            print(f"{path}: modified lines/replacements: {result.changed}", file=sys.stderr)
        else:
            print(f"Modified lines/replacements: {result.changed}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
