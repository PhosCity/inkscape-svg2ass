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

__version__ = "1.0.5"

import inkex


def round_number(num, decimals=3):
    rounded = round(float(num), decimals)
    return int(rounded) if rounded.is_integer() else rounded


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
        prev_cmd = None
        for idx, segment in enumerate(elem):
            cmd = (segment.letter).lower()
            if cmd == "z":
                continue
            cmd = "b" if cmd == "c" else cmd
            if cmd != prev_cmd:
                path.append(cmd)
                prev_cmd = cmd
            path.extend([round_number(num) for num in segment.args])
        return " ".join(map(str, path))

    def create_ass_tags(self, elem):
        def get_alpha_attribute(style, attrib):
            if opacity := style.get(attrib):
                opacity = float(opacity)
                if opacity != 1.0:
                    return f"&H{int((1 - opacity) * 255):02X}&"
            return False

        def get_color_attribute(style, attrib):
            color_attr = style(attrib)

            if color_attr is None:
                return False

            if isinstance(color_attr, inkex.LinearGradient):
                # Get first color of the gradient for now
                first_stop = color_attr.href.stops[0]
                fisrt_stop_style = first_stop.specified_style()
                color_str = fisrt_stop_style.get("stop-color")

                # # TODO: Add support for linear gradients.
                # # Retrieve gradient attributes
                # x1 = color_attr.get("x1", "0%")
                # y1 = color_attr.get("y1", "0%")
                # x2 = color_attr.get("x2", "100%")
                # y2 = color_attr.get("y2", "0%")
                # inkex.errormsg(f"x1: {x1}, y1: {y1}, x2: {x2}, y2: {y2}")
                # # Process stops
                # for stop in color_attr.href.stops:
                #     stop_style = stop.specified_style()
                #     color = stop_style.get("stop-color")
                #     opacity = stop_style.get("stop-opacity")
                #     offset = stop.attrib.get("offset")
                #     inkex.errormsg(f"color: {color}, opacity: {opacity}, offset: {offset}")

            # elif isinstance(color_attr, inkex.RadialGradient):
            #     inkex.utils.debug("It's radial gradient.")
            else:
                color_str = color_attr

            try:
                color = inkex.Color(color_str)
                r, g, b = color.to_rgb()
                bgr_hex = f"&H{b:02X}{g:02X}{r:02X}&"
                return bgr_hex
            except inkex.ColorIdError:
                return False

        def get_stroke_width_attribute(style):
            stroke_width = style.get("stroke-width")
            if not stroke_width:
                return False

            paint_order = style.get("paint-order", "normal")
            if paint_order == "normal":
                paint_order = "fill stroke markers"

            paint_order = paint_order.split()
            if paint_order.index("stroke") < paint_order.index("fill"):
                return round_number(stroke_width, 2) * 0.5
            else:
                # TODO: For the most accurate representation of stroke, we need to offset the path inwards by half of stroke width
                return round_number(stroke_width, 2)

        style = elem.specified_style()
        ass_tags = {
            "an": 7,
            "bord": 0,
            "shad": 0,
            "fscx": 100,
            "fscy": 100,
            "pos": [0, 0],
        }

        if opacity := get_alpha_attribute(style, "opacity"):
            ass_tags["alpha"] = opacity

        if fill_color := get_color_attribute(style, "fill"):
            ass_tags["c"] = fill_color

            if fill_opacity := get_alpha_attribute(style, "fill-opacity"):
                ass_tags["1a"] = fill_opacity
        else:
            ass_tags["1a"] = "&HFF&"

        stroke_color = get_color_attribute(style, "stroke")
        if (stroke_width := get_stroke_width_attribute(style)) and stroke_color:
            ass_tags["bord"] = stroke_width
            ass_tags["3c"] = stroke_color

            if stroke_opacity := get_alpha_attribute(style, "stroke-opacity"):
                ass_tags["3a"] = stroke_opacity

        ass_tags["p"] = 1

        return ass_tags

    def create_clips(self, elem, ass_tags):
        clip_path = elem.get("clip-path")
        if clip_path is None:
            return ass_tags

        clip_path = clip_path[5:-1]  # Extract the ID between 'url(#' and ')'
        clip_elem = self.svg.getElementById(clip_path)
        ass_tags["clip"] = f"({self.process_path(clip_elem.to_path_element())})"
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
            ass_tags = self.create_ass_tags(elem)
            ass_tags = self.create_clips(elem, ass_tags)
            # Convert non-path elements to paths
            if elem.TAG != "path":
                elem = elem.to_path_element()
            path = self.process_path(elem)
            return self.generate_lines(path, ass_tags)

    def recurse_into_group(self, group):
        for child in group:
            if isinstance(child, inkex.Group):
                self.recurse_into_group(child)
            elif isinstance(child, inkex.ShapeElement):
                if line := self.process_svg_element(child):
                    inkex.utils.debug(line)

    def effect(self):
        # This grabs selected objects by z-order, ordered from bottom to top
        selection_list = self.svg.selection.rendering_order()
        if len(selection_list) == 0:
            inkex.errormsg("No object was selected!")
            return

        for elem in selection_list:
            if isinstance(elem, inkex.Group):
                elem.bake_transforms_recursively()
                self.recurse_into_group(elem)
            elif isinstance(elem, inkex.ShapeElement):
                if line := self.process_svg_element(elem):
                    inkex.utils.debug(line)


if __name__ == "__main__":
    ConvertToASS().run()
