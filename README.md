# th2-tool

Small Python CLI to modify Therion `.th2` files generated from TopoDroid to work better with Therion cartography style, and `.th` centerline files.

## Quick Start

Run the script directly:

```bash
python3 th2_edit.py <file.th|file.th2|directory> [command] [options]
```

From this folder:

```bash
python3 -m unittest discover -s tests
```

If no command is provided for a `.th2` file, the script applies all default conversions:

- `line pit` -> `line floor-step`
- `line chimney` -> `line ceiling-step -reverse on`
- `line rock-border` -> add or force `-close on`

For `.th` files, the script performs only backsight marking: it marks the station-to-station shot immediately after each `extend left` command as `duplicate`. This matches TopoDroid's backsight-before-foresight layout, retaining the backsight as survey data while excluding it from Therion's total-length calculation. The `.th2` conversions and commands do not modify `.th` files.

## Project Layout

- `th2_edit.py`: main CLI script.
- `tests/`: unit tests for conversion and CLI behavior.
- `data/`: sample and working `.th2` files (for example `data/AS-1p.th2`).

Run commands from the repository root so paths like `./data/AS-1p.th2` work as shown.

## Examples

Default conversion (no command):

```bash
python3 th2_edit.py ./data/AS-1p.th2 --in-place
```

Mark backsights in a centerline file (enabled by default):

```bash
python3 th2_edit.py ./data/Canyon.th --in-place
```

Leave `.th` backsights unmodified:

```bash
python3 th2_edit.py ./data/Canyon.th --no-mark-backsights --in-place
```

Process every `.th` and `.th2` file directly in a directory. Directory input always writes changes in place without creating backups:

```bash
python3 th2_edit.py ./data --no-backup
```

## Notes

- `--in-place` and `--output` are mutually exclusive.
- Single-file in-place changes create `<name>.<extension>.bak` by default; unchanged files are not rewritten or backed up.
- Use `--no-backup` to disable backup creation.
- `--mark-backsights` is enabled by default for `.th` inputs; use `--no-mark-backsights` to disable it.
- Directory input processes only immediate `.th` and `.th2` files, not subdirectories. It always writes changes in place without backups and cannot be used with `--output`.
