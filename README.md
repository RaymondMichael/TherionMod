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

Replace all `rock-border` to `rock-edge` and write to a new file:

```bash
python3 th2_edit.py ./data/AS-1p.th2 replace \
  --find "rock-border" \
  --replace "rock-edge" \
  --output ./a_edited.th2
```

Set `-close off` for all border lines in place (with `.bak` backup):

```bash
python3 th2_edit.py ./data/AS-1p.th2 set-option \
  --match "^line border" \
  --option close \
  --value off \
  --in-place
```

Delete `-subtype` from matching lines:

```bash
python3 th2_edit.py ./data/AS-1p.th2 delete-option \
  --match "^line border" \
  --option subtype \
  --output ./a_without_subtype.th2
```

Default conversion (no command):

```bash
python3 th2_edit.py ./data/AS-1p.th2 --in-place
```

Equivalent explicit form:

```bash
python3 th2_edit.py ./data/AS-1p.th2 all-conversions --in-place
```

Convert all `line pit` to `line floor-step`:

```bash
python3 th2_edit.py ./data/AS-1p.th2 pit-to-floor-step --in-place
```

Convert all `line rock-border` to include `-close on`:

```bash
python3 th2_edit.py ./data/AS-1p.th2 rock-border-close-on --in-place
```

## Notes

- `--in-place` and `--output` are mutually exclusive.
- By default, `--in-place` creates `<name>.th2.bak`.
- Use `--no-backup` to disable backup creation.
