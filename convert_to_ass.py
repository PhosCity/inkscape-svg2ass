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

__version__ = "1.0.1"

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
        path = []
        prevCmd = None
        for idx, segment in enumerate(elem):
            cmd = segment.letter
            args = segment.args
            # Round the values to three digits
            args = [round(num, 3) if isinstance(num, float) else num for num in args]
            if cmd == "M":
                path.append("m")
                path.extend(args)
                startX, startY = args
            elif cmd == "L":
                if prevCmd != cmd:
                    path.append("l")
                path.extend(args)
            elif cmd == "C":
                if prevCmd != cmd:
                    path.append("b")
                path.extend(args)
            elif cmd == "Z":
                if prevCmd != "L":
                    path.append("l")
                path.extend([startX, startY])
                del startX, startY
            prevCmd = cmd
        return " ".join(map(str, path))

    def create_ass_tags(self, elem):
        def decimal_to_hex(value):
            value = max(0, min(1, float(value)))
            return f"&H{int((1 - value) * 255):02X}&"

        def get_color_attribute(style, attrib):
            color_attr = style.get(attrib)
            if not color_attr or color_attr == "none":
                return "black"

            color_str = None
            # Get first color of the gradient for now
            if color_attr and color_attr.startswith("url("):
                gradient_id = color_attr[5:-1]  # Extract the ID between 'url(#' and ')'

                # Retrieve the gradient object by its ID
                gradient = self.svg.getElementById(gradient_id)

                if isinstance(gradient, inkex.LinearGradient):
                    start_stop = gradient.stops[1]
                    style = start_stop.specified_style()
                    color_str = style.get("stop-color")
                # TODO: Add support for linear gradients.
                #     # Retrieve gradient attributes
                #     x1 = gradient.get("x1", "0%")
                #     y1 = gradient.get("y1", "0%")
                #     x2 = gradient.get("x2", "100%")
                #     y2 = gradient.get("y2", "0%")
                #     # Process stops
                #     for stop in gradient.stops:
                #         style = stop.specified_style()
                #         color = style.get("stop-color")
                #         opacity = style.get("stop-opacity")
                #         offset = stop.attrib.get("offset")
                # elif isinstance(gradient, inkex.RadialGradient):
                #     inkex.utils.debug("It's radial gradient.")
                #     # self.process_radial_gradient(gradient)
            else:
                color_str = color_attr

            if not color_str:
                return False

            try:
                color = inkex.Color(color_str)
                r, g, b = color.to_rgb()
                bgr_hex = f"&H{b:02X}{g:02X}{r:02X}&"
                return bgr_hex
            except inkex.ColorIdError:
                return False

        style = elem.specified_style()
        ass_tags = {"an": 7, "bord": 0, "shad": 0, "pos": [0, 0]}

        if fill_color := get_color_attribute(style, "fill"):
            ass_tags["c"] = fill_color

            if fill_opacity := style.get("fill-opacity"):
                ass_tags["1a"] = decimal_to_hex(fill_opacity)

        if stroke_color := get_color_attribute(style, "stroke"):
            ass_tags["3c"] = stroke_color

            if stroke_width := style.get("stroke-width"):
                stroke_width = (
                    int(stroke_width) if stroke_width.isdigit() else float(stroke_width)
                )
                # Due to the different semantics of SVG strokes and ASS borders, I'm hard-coding a factor by which we'll change the stroke width
                # This only works for some stroke order.
                stroke_width = stroke_width * 0.52549918642
                ass_tags["bord"] = round(stroke_width, 2)

            if stroke_opacity := style.get("stroke-opacity"):
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

    def recurse_into_group(self, group):
        lines = []
        for child in group:
            if isinstance(child, inkex.Group):
                self.recurse_into_group(child)
            elif isinstance(child, inkex.ShapeElement):
                line = self.process_svg_element(child)
                if line := self.process_svg_element(child):
                    lines.append(line)
        return lines

    def effect(self):
        lines = []

        # This grabs selected objects by z-order, ordered from bottom to top
        selection_list = self.svg.selection.rendering_order()
        if len(selection_list) < 1:
            inkex.errormsg("No object was selected!")
            return

        for elem in selection_list:
            if isinstance(elem, inkex.Group):
                group_lines = self.recurse_into_group(elem)
                if len(group_lines):
                    lines.extend(group_lines)
            elif isinstance(elem, inkex.ShapeElement):
                line = self.process_svg_element(elem)
                if line:
                    lines.append(line)

        for line in lines:
            inkex.utils.debug(line)


if __name__ == "__main__":
    ConvertToASS().run()
