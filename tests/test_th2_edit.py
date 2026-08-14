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
    mark_backsights_as_duplicate,
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

    def test_add_section_lines_for_scraps_preserves_tab_indentation(self) -> None:
        src = (
            "scrap demo -projection plan\n"
            "\tline wall\n"
            "\t\t0 0\n"
            "\tendline\n"
            "point 10 20 section -scrap AS-xs-AS12\n"
            "point 100 200 station -name \"AS12\"\n"
        )

        result = add_section_lines_for_scraps(src)

        self.assertEqual(result.changed, 1)
        self.assertIn("line section -direction both\n\t90 210\n\t110 190\n\tsmooth off\nendline\n", result.text)

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

    def test_mark_backsights_marks_station_leg_after_extend_left(self) -> None:
        src = (
            "    extend left\n"
            "    GN2 GN1 13.10 14.2 -2.9\n"
            "    # extend auto\n"
            "    GN2 - 3.50 284.9 0.0\n"
            "    extend right\n"
            "    GN1 GN2 13.20 194.9 3.1\n"
        )

        result = mark_backsights_as_duplicate(src)

        self.assertEqual(result.changed, 1)
        self.assertEqual(
            result.text,
            "    extend left\n"
            "    flags duplicate\n"
            "    GN2 GN1 13.10 14.2 -2.9\n"
            "    flags not duplicate\n"
            "    # extend auto\n"
            "    GN2 - 3.50 284.9 0.0\n"
            "    extend right\n"
            "    GN1 GN2 13.20 194.9 3.1\n",
        )

    def test_mark_backsights_is_idempotent(self) -> None:
        src = "extend left\nGN2 GN1 13.10 14.2 -2.9\n"

        first_result = mark_backsights_as_duplicate(src)
        second_result = mark_backsights_as_duplicate(first_result.text)

        self.assertEqual(second_result.changed, 0)
        self.assertEqual(second_result.text, first_result.text)

    def test_default_command_marks_backsights_in_th_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "in.th"
            output_path = tmp_path / "out.th"
            input_path.write_text(
                "line pit\nextend left\nGN2 GN1 13.10 14.2 -2.9\n",
                encoding="utf-8",
            )

            exit_code = main([str(input_path), "--output", str(output_path)])

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "line pit\nextend left\nflags duplicate\nGN2 GN1 13.10 14.2 -2.9\nflags not duplicate\n",
            )

    def test_no_mark_backsights_leaves_th_file_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "in.th"
            output_path = tmp_path / "out.th"
            source = "extend left\nGN2 GN1 13.10 14.2 -2.9\n"
            input_path.write_text(source, encoding="utf-8")

            exit_code = main([str(input_path), "--no-mark-backsights", "--output", str(output_path)])

            self.assertEqual(exit_code, 0)
            self.assertEqual(output_path.read_text(encoding="utf-8"), source)

    def test_directory_input_processes_th_and_th2_files_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            th_path = tmp_path / "survey.th"
            th2_path = tmp_path / "drawing.th2"
            ignored_path = tmp_path / "notes.txt"
            nested_path = tmp_path / "nested"
            th_path.write_text("extend left\nGN2 GN1 13.10 14.2 -2.9\n", encoding="utf-8")
            th2_path.write_text("line pit\n", encoding="utf-8")
            ignored_path.write_text("line pit\n", encoding="utf-8")
            nested_path.mkdir()
            (nested_path / "nested.th2").write_text("line pit\n", encoding="utf-8")

            exit_code = main([str(tmp_path), "--no-backup"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                th_path.read_text(encoding="utf-8"),
                "extend left\nflags duplicate\nGN2 GN1 13.10 14.2 -2.9\nflags not duplicate\n",
            )
            self.assertEqual(th2_path.read_text(encoding="utf-8"), "line floor-step\n")
            self.assertEqual(ignored_path.read_text(encoding="utf-8"), "line pit\n")
            self.assertEqual((nested_path / "nested.th2").read_text(encoding="utf-8"), "line pit\n")

    def test_directory_input_does_not_create_backups(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            changed_path = tmp_path / "drawing.th2"
            unchanged_path = tmp_path / "survey.th"
            changed_path.write_text("line pit\n", encoding="utf-8")
            unchanged_path.write_text("extend left\nflags duplicate\nGN2 GN1 13.10 14.2 -2.9\n", encoding="utf-8")

            exit_code = main([str(tmp_path)])

            self.assertEqual(exit_code, 0)
            self.assertFalse(changed_path.with_suffix(".th2.bak").exists())
            self.assertFalse(unchanged_path.with_suffix(".th.bak").exists())

    def test_in_place_edits_preserve_crlf_line_endings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            th_path = tmp_path / "survey.th"
            th2_path = tmp_path / "drawing.th2"
            th_path.write_bytes(b"extend left\r\nGN2 GN1 13.10 14.2 -2.9\r\n")
            th2_path.write_bytes(b"line pit\r\n")

            self.assertEqual(main([str(th_path), "--in-place", "--no-backup"]), 0)
            self.assertEqual(main([str(th2_path), "--in-place", "--no-backup"]), 0)

            self.assertEqual(
                th_path.read_bytes(),
                b"extend left\r\nflags duplicate\r\nGN2 GN1 13.10 14.2 -2.9\r\nflags not duplicate\r\n",
            )
            self.assertEqual(th2_path.read_bytes(), b"line floor-step\r\n")


if __name__ == "__main__":
    unittest.main()
