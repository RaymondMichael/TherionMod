# th2-tool

Small Python CLI to modify Therion `.th2` files generated from TopoDroid to work better with Therion cartography style.

## Quick Start

Run the script directly:

```bash
python3 th2_edit.py <file.th2> [command] [options]
```

From this folder:

```bash
python3 -m unittest discover -s tests
```

If no command is provided, the script applies all default conversions:

- `line pit` -> `line floor-step`
- `line chimney` -> `line ceiling-step -reverse on`
- `line rock-border` -> add or force `-close on`

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

## Notes

- `--in-place` and `--output` are mutually exclusive.
- By default, `--in-place` creates `<name>.th2.bak`.
- Use `--no-backup` to disable backup creation.
