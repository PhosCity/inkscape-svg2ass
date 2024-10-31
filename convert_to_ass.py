#!/usr/bin/env python
# coding=utf-8
#
# Copyright (C) 2024 PhosCity
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import inkex


class ConvertToASS(inkex.EffectExtension):
    def add_arguments(self, pars):
        pars.add_argument("--output_format", type=str, help="types of output")

    def process_path(self, elem):
        # Apply any transformations and viewBox scaling
        elem.apply_transform()
        # Convert commands like A, S, Q, and T to cubic bezier
        elem = elem.path.to_superpath().to_path()
        # Convert all commands to absolute positions
        elem = elem.to_absolute()

        # After this, path will now contain only M, L, C, and Z commands
        path = ""
        prevCmd = None
        for idx, segment in enumerate(elem):
            cmd = segment.letter
            args = segment.args
            # Round the values to three digits
            args = [round(num, 3) if isinstance(num, float) else num for num in args]
            if cmd == "M":
                path += f"m {args[0]} {args[1]}"
                startX = args[0]
                startY = args[1]

            elif cmd == "L":
                if prevCmd != cmd:
                    path += " l"
                path += f" {args[0]} {args[1]}"

            elif cmd == "C":
                if prevCmd != cmd:
                    path += " b"
                path += f" {args[0]} {args[1]} {args[2]} {args[3]} {args[4]} {args[5]}"

            elif cmd == "Z":
                if prevCmd != "L":
                    path += " l"
                path += f" {startX} {startY} "
                del startX, startY
            prevCmd = cmd
        return path

    def create_ass_tags(self, elem):
        def decimal_to_hex(value):
            value = max(0, min(1, float(value)))
            return f"&H{int((1 - value) * 255):02X}&"

        def color_to_bgr(color_str):
            try:
                color = inkex.Color(color_str)
                r, g, b = color.to_rgb()
                bgr_hex = f"&H{b:02X}{g:02X}{r:02X}&"
                return bgr_hex
            # Catch exception due to color of gradient. Gradient is ignored for now.
            except inkex.ColorIdError:
                return False

        def get_attribute(style, attrib):
            attr = elem.attrib.get(attrib)
            if attrib in style:
                attr = style.get(attrib)
            if attr and attr != "none":
                return attr
            return False

        style = elem.style
        ass_tags = {"an": 7, "bord": 0, "shad": 0, "pos": [0, 0]}

        if fill_color := get_attribute(style, "fill"):
            if color := color_to_bgr(fill_color):
                ass_tags["c"] = color

            if fill_opacity := get_attribute(style, "fill-opacity"):
                ass_tags["1a"] = decimal_to_hex(fill_opacity)

        if stroke_color := get_attribute(style, "stroke"):
            if color := color_to_bgr(stroke_color):
                ass_tags["3c"] = color

            if stroke_width := get_attribute(style, "stroke-width"):
                ass_tags["bord"] = (
                    int(stroke_width)
                    if stroke_width.isdigit()
                    else round(float(stroke_width), 2)
                )

            if stroke_opacity := get_attribute(style, "stroke-opacity"):
                ass_tags["3a"] = decimal_to_hex(stroke_opacity)

        ass_tags["p"] = 1

        return ass_tags

    def generate_lines(self, path, ass_tags):
        tags = []
        for key, value in ass_tags.items():
            if isinstance(value, list):
                value_str = f"({value[0]},{value[1]})"
            else:
                value_str = str(value)
            tags.append(f"\\{key}{value_str}")
        tags_string = "{" + "".join(tags) + "}"
        path = path.strip()
        if self.options.output_format == "drawing":
            line = tags_string + path
        elif self.options.output_format == "clip":
            line = "\\clip(" + path + ")"
        elif self.options.output_format == "iclip":
            line = "\\iclip(" + path + ")"
        elif self.options.output_format == "line":
            line = (
                "Dialogue: 0,0:00:00.00,0:00:00.02,Default,,0,0,0,,"
                + tags_string
                + path
            )
        return line

    def process_svg_element(self, elem):
        if elem.TAG in {
            "path",
            "rect",
            "circle",
            "ellipse",
            "line",
            "polyline",
            "polygon",
        }:
            # Convert non-path elements to paths
            if elem.TAG != "path":
                elem = elem.to_path_element()
            path = self.process_path(elem)
            ass_tags = self.create_ass_tags(elem)
            return self.generate_lines(path, ass_tags)

    def effect(self):
        page_list = self.svg.xpath("//inkscape:transform")

        if len(page_list) > 1:
            page_x_translate_list = []

            for page in page_list:
                x_translate = page.get("x")
                y_translate = page.get("y")
                page_x_translate_list.append([x_translate, y_translate])
            inkex.errormsg(page_x_translate_list)

        lines = []

        selection_list = self.svg.selected

        if len(selection_list) < 1:
            inkex.errormsg("No object was selected!")
            return

        for elem in selection_list:
            if elem.TAG == "g":
                for child in elem.iterchildren():
                    line = self.process_svg_element(child)
                    if line:
                        lines.append(line)
            else:
                line = self.process_svg_element(elem)
                if line:
                    lines.append(line)
        for line in reversed(lines):
            inkex.utils.debug(line)


if __name__ == "__main__":
    ConvertToASS().run()
