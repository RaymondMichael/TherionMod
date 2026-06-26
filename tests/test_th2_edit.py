from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from th2_edit import (
    add_section_lines_for_scraps,
    convert_chimney_to_ceiling_step,
    convert_pit_to_floor_step,
    convert_rock_border_close_on,
    delete_option,
    main,
    replace_text,
    set_option,
)


class Th2EditTests(unittest.TestCase):
    def test_replace_literal(self) -> None:
        src = "line rock-border\nendline\n"
        result = replace_text(src, "rock-border", "rock-edge", regex=False)
        self.assertEqual(result.changed, 1)
        self.assertIn("rock-edge", result.text)

    def test_set_option_updates_existing(self) -> None:
        src = "line border -close on\n"
        result = set_option(src, r"^line border", "close", "off")
        self.assertEqual(result.changed, 1)
        self.assertEqual(result.text, "line border -close off\n")

    def test_set_option_appends_missing(self) -> None:
        src = "line wall\n"
        result = set_option(src, r"^line wall", "subtype", "invisible")
        self.assertEqual(result.changed, 1)
        self.assertEqual(result.text, "line wall -subtype invisible\n")

    def test_delete_option(self) -> None:
        src = "line border -id l1 -close on -subtype invisible\n"
        result = delete_option(src, r"^line border", "subtype")
        self.assertEqual(result.changed, 1)
        self.assertEqual(result.text, "line border -id l1 -close on\n")

    def test_pit_to_floor_step(self) -> None:
        src = "line pit -id l22\nline wall\nline pit\n"
        result = convert_pit_to_floor_step(src)
        self.assertEqual(result.changed, 2)
        self.assertEqual(result.text, "line floor-step -id l22\nline wall\nline floor-step\n")

    def test_default_command_runs_all_conversions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "in.th2"
            output_path = tmp_path / "out.th2"
            input_path.write_text("line pit\nline chimney\nline rock-border\nline wall\n", encoding="utf-8")

            exit_code = main([str(input_path), "--output", str(output_path)])

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "line floor-step\nline ceiling-step -reverse on\nline rock-border -close on\nline wall\n",
            )

    def test_chimney_to_ceiling_step_adds_reverse(self) -> None:
        src = "line chimney -id l9\nline wall\n"
        result = convert_chimney_to_ceiling_step(src)
        self.assertEqual(result.changed, 1)
        self.assertEqual(result.text, "line ceiling-step -id l9 -reverse on\nline wall\n")

    def test_chimney_to_ceiling_step_forces_reverse_on(self) -> None:
        src = "line chimney -reverse off\n"
        result = convert_chimney_to_ceiling_step(src)
        self.assertEqual(result.changed, 1)
        self.assertEqual(result.text, "line ceiling-step -reverse on\n")

    def test_rock_border_close_on_adds_option(self) -> None:
        src = "line rock-border -id r2\nline wall\n"
        result = convert_rock_border_close_on(src)
        self.assertEqual(result.changed, 1)
        self.assertEqual(result.text, "line rock-border -id r2 -close on\nline wall\n")

    def test_rock_border_close_on_forces_on(self) -> None:
        src = "line rock-border -close off\n"
        result = convert_rock_border_close_on(src)
        self.assertEqual(result.changed, 1)
        self.assertEqual(result.text, "line rock-border -close on\n")

    def test_add_section_lines_for_scraps_inserts_before_matching_station(self) -> None:
        src = (
            "scrap demo -projection plan\n"
            "point 10 20 section -scrap AS-xs-AS12\n"
            "\n"
            "point 100 200 station -name \"AS12\"\n"
            "endscrap\n"
        )

        result = add_section_lines_for_scraps(src)

        self.assertEqual(result.changed, 1)
        self.assertEqual(
            result.text,
            "scrap demo -projection plan\n"
            "point 10 20 section -scrap AS-xs-AS12\n"
            "\n"
            "line section -direction both\n"
            "  90 210\n"
            "  110 190\n"
            "  smooth off\n"
            "endline\n"
            "\n"
            "point 100 200 station -name \"AS12\"\n"
            "endscrap\n",
        )

    def test_add_section_lines_for_scraps_is_idempotent_when_adjacent_line_exists(self) -> None:
        src = (
            "point 10 20 section -scrap AS-xs-AS12\n"
            "\n"
            "line section -direction both\n"
            "  90 210\n"
            "  110 190\n"
            "  smooth off\n"
            "endline\n"
            "\n"
            "point 100 200 station -name \"AS12\"\n"
        )

        result = add_section_lines_for_scraps(src)

        self.assertEqual(result.changed, 0)
        self.assertEqual(result.text, src)

    def test_default_command_adds_section_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "in.th2"
            output_path = tmp_path / "out.th2"
            input_path.write_text(
                "point 10 20 section -scrap AS-xs-AS12\n"
                "\n"
                "point 100 200 station -name \"AS12\"\n",
                encoding="utf-8",
            )

            exit_code = main([str(input_path), "--output", str(output_path)])

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "point 10 20 section -scrap AS-xs-AS12\n"
                "\n"
                "line section -direction both\n"
                "  90 210\n"
                "  110 190\n"
                "  smooth off\n"
                "endline\n"
                "\n"
                "point 100 200 station -name \"AS12\"\n",
            )


if __name__ == "__main__":
    unittest.main()
