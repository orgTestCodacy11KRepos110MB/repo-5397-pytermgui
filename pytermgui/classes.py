"""
pytermgui.classes
-----------------
author: bczsalba


This module provides the classes used by the module.
"""

# these classes will have to have more than 7 attributes mostly.
# pylint: disable=too-many-instance-attributes

from __future__ import annotations
from typing import Optional, Callable

from .helpers import real_length
from .context_managers import cursor_at
from .ansi_interface import (
    background16,
    screen_width,
    screen_height,
    screen_size,
    clear,
)

StyleType = Callable[[int, str], str]


def default_foreground(depth: int, item: str) -> str:
    """Default foreground style"""

    _ = depth
    return item


def default_background(depth: int, item: str) -> str:
    """Default background style"""

    return background16(item, 30 + depth)


class BaseElement:
    """The element from which all UI classes derive from"""

    def __init__(self, width: int = 0, pos: Optional[tuple[int, int]] = None) -> None:
        """Initialize universal data for objects"""

        self.forced_width: Optional[int] = None
        self.forced_height: Optional[int] = None

        self._width = width
        self._height = 1

        if pos is None:
            pos = 1, 1
        self.pos = pos

        self.depth = 0
        self.styles: dict[str, StyleType] = {}
        self.chars: dict[str, list[str]] = {}

        self.is_selectable = False
        self.selectables_length = 0
        self.selected_index: Optional[int] = None

    def __repr__(self) -> str:
        """Print self.dbg() by default"""

        return self.dbg()

    @property
    def width(self) -> int:
        """Getter for width property"""

        return self._width

    @width.setter
    def width(self, value: int) -> None:
        """Setter for width property"""

        if self.forced_width is not None and value is not self.forced_width:
            raise TypeError(
                "It is impossible to manually set the width "
                + "of an object with a `forced_width` attribute."
            )

        self._width = value

    @property
    def height(self) -> int:
        """Getter for height property"""

        return self._height

    @height.setter
    def height(self, value: int) -> None:
        """Non-setter for height property"""

        raise TypeError(
            "`element.height` is not settable, it is currently "
            + f"{self.height}. Use element.forced_height instead."
        )

    def set_style(self, key: str, value: StyleType) -> None:
        """Set self.{key}_style to value"""

        if not key in self.styles.keys():
            raise KeyError(f"Style {key} is not valid for {type(self)}!")

        if not callable(value):
            raise ValueError(f"Style {key} for {type(self)} has to be a callable.")

        self.styles[key] = value

    def set_char(self, key: str, value: list[str]) -> None:
        """Set self.{key}_char to value"""

        if not key in self.chars.keys():
            raise KeyError(f"Char {key} is not valid for {type(self)}!")

        self.chars[key] = value

    def get_style(self, key: str) -> StyleType:
        """Try to get style"""

        return self.styles[key]

    def get_char(self, key: str) -> list[str]:
        """Try to get char"""

        return self.chars[key]

    def get_lines(self) -> list[str]:
        """Stub for element.get_lines"""

        return [type(self).__name__]

    @property
    def posx(self) -> int:
        """Return x position of object"""

        return self.pos[0]

    @posx.setter
    def posx(self, value: int) -> None:
        """Set x position of object"""

        if not isinstance(value, int):
            raise NotImplementedError("You can only set integers as object positions.")

        self.pos = (value, self.posy)

    @property
    def posy(self) -> int:
        """Return y position of object"""

        return self.pos[1]

    @posy.setter
    def posy(self, value: int) -> None:
        """Set y position of object"""

        if not isinstance(value, int):
            raise NotImplementedError("You can only set integers as object positions.")

        self.pos = (self.posx, value)

    def select(self, index: int) -> None:
        """Select part of self"""

        if not self.is_selectable:
            raise TypeError(f"Object of type {type(self)} is marked non-selectable.")

        index = min(max(0, index), self.selectables_length - 1)
        self.selected_index = index

    def dbg(self) -> str:
        """Debug identifiable information about object"""

        return type(self).__name__ + "()"


class Container(BaseElement):
    """The element that serves as the outer parent to all other elements"""

    VERT_ALIGN_TOP = 0
    VERT_ALIGN_CENTER = 1
    VERT_ALIGN_BOTTOM = 2

    HORIZ_ALIGN_LEFT = 3
    HORIZ_ALIGN_CENTER = 4
    HORIZ_ALIGN_RIGHT = 5

    CENTER_X = 6
    CENTER_Y = 7
    CENTER_BOTH = 8

    def __init__(
        self,
        width: int = 0,
        horiz_align: int = HORIZ_ALIGN_CENTER,
        vert_align: int = VERT_ALIGN_CENTER,
    ) -> None:
        """Initialize Container data"""

        super().__init__(width)
        self._elements: list[BaseElement] = []
        self._selectables: dict[int, tuple[BaseElement, int]] = {}
        self._centered_axis: Optional[int] = None
        self._prev_selected: Optional[BaseElement] = None

        self._prev_screen: tuple[int, int] = (0, 0)

        self.vert_align = vert_align
        self.horiz_align = horiz_align
        self.styles = {
            "border": default_foreground,
            "corner": default_foreground,
        }

        self.chars = {
            "border": ["| ", "-", " |", "-"],
            "corner": [""] * 4,
        }

    @property
    def sidelength(self) -> int:
        """Returns length of left+right borders"""

        left_border, _, right_border, _ = self.chars["border"]
        return real_length(left_border + right_border)

    @property
    def selected(self) -> Optional[BaseElement]:
        """Return selected object"""

        if self.selected_index is None:
            return None

        data = self._selectables.get(self.selected_index)
        if data is None:
            return data

        self._prev_selected = data[0]
        return data[0]

    def __iadd__(self, other: object) -> Optional[Container]:
        """Call self._add_element(other) and return self"""

        if not isinstance(other, BaseElement):
            raise NotImplementedError(
                "You can only add BaseElements to other BaseElements."
            )

        self._add_element(other)
        return self

    def __add__(self, other: object) -> None:
        """Call self._add_element(other)"""

        self.__iadd__(other)

    def _add_element(self, other: BaseElement) -> None:
        """Add other to self._elements"""

        if self.forced_width is not None and other.forced_width is not None:
            if self.forced_width < other.forced_width:
                raise ValueError(
                    "Object being added has a forced width that is larger than self."
                    + f" ({other.forced_width} > {self.forced_width})"
                )

        self._elements.append(other)
        if isinstance(other, Container):
            other.set_recursive_depth(self.depth + 2)
        else:
            other.depth = self.depth + 1

        other.get_lines()

        if not len(keys := list(self._selectables)) > 0:
            sel_len = 0
        else:
            sel_len = max(keys) + 1

        for i in range(other.selectables_length):
            self._selectables[sel_len + i] = other, i

        self._height += other.height
        self.get_lines()

    def dbg(self) -> str:
        """Return dbg information about this object's elements"""

        out = "Container(), elements=["
        for element in self._elements:
            out += type(element).__name__ + ", "

        out = out.strip(", ")
        out += "]"

        return out

    def set_recursive_depth(self, value: int) -> None:
        """Set depth for all children, recursively"""

        self.depth = value
        for element in self._elements:
            if isinstance(element, Container):
                element.set_recursive_depth(value + 1)
            else:
                element.depth = value

    def get_lines(self) -> list[str]:
        """Get lines to represent the object"""

        # pylint: disable=too-many-locals, too-many-branches
        #  All the locals here are used,
        # reducing their number would make the code less readable
        # This method might need a refactor because of the branches
        # issue, but I don't see what could really be improved.

        def _apply_forced_width(source: BaseElement, target: BaseElement) -> bool:
            """Apply source's forced_width attribute to target, return False if not possible."""

            if source.forced_width is not None and not target.forced_width is not None:
                source.width = source.forced_width
                if source.width > target.width - self.sidelength:
                    target.width = source.width + self.sidelength

                return True

            return False

        def _create_border_line(left: str, middle: str, right: str) -> str:
            """Create border line by combining left + middle + right"""

            corner_len = real_length(left + right)

            # pad middle if theres no length
            if real_length(middle) == 0:
                middle = " "

            return (
                corner_style(self.depth, left)
                + border_style(self.depth, (self.width - corner_len) * middle)
                + corner_style(self.depth, right)
            )

        lines: list[str] = []

        borders = self.get_char("border")
        left_border, top_border, right_border, bottom_border = borders

        corners = self.get_char("corner")
        top_left, top_right, bottom_right, bottom_left = corners

        corner_style = self.get_style("corner")
        border_style = self.get_style("border")

        has_height_remaining = True
        for element in self._elements:
            if not has_height_remaining:
                break

            if not _apply_forced_width(element, self):
                _apply_forced_width(self, element)

            # Container()-s need an extra padding
            container_offset = 1 if not isinstance(element, Container) else 0

            if element.width >= self.width and not self.forced_width is not None:
                self.width = element.width + self.sidelength + container_offset

            elif not element.forced_width is not None:
                element.width = self.width - self.sidelength - container_offset

            for line in element.get_lines():
                if (
                    self.forced_height is not None
                    and len(lines) + 2 >= self.forced_height
                ):
                    has_height_remaining = False
                    break

                if (
                    self.forced_width is not None
                    and (other_len := real_length(line)) + self.sidelength
                    > self.forced_width
                ):
                    raise ValueError(
                        f"Object `{element.dbg()}` "
                        + "could not be resized to self.forced_width. "
                        + f"({other_len} > {self.forced_width}) "
                    )

                if self.horiz_align is Container.HORIZ_ALIGN_CENTER:
                    side_padding = (
                        (self.width - real_length(line) - self.sidelength) // 2 * " "
                    )

                elif self.horiz_align is Container.HORIZ_ALIGN_LEFT:
                    side_padding = ""

                elif self.horiz_align is Container.HORIZ_ALIGN_RIGHT:
                    side_padding = (
                        self.width - real_length(line) - self.sidelength
                    ) * " "

                lines.append(
                    border_style(self.depth, left_border)
                    + side_padding
                    + line
                    + (self.width - self.sidelength - real_length(line + side_padding))
                    * " "
                    + border_style(self.depth, right_border)
                )

        if self.forced_height is not None:
            padding_range = self.forced_height - len(lines) - 2
            empty_line = (
                left_border + (self.width - self.sidelength) * " " + right_border
            )

            if self.vert_align is Container.VERT_ALIGN_TOP:
                for _ in range(padding_range):
                    lines.append(empty_line)

            elif self.vert_align is Container.VERT_ALIGN_CENTER:
                for _ in range(padding_range // 2):
                    lines.insert(0, empty_line)
                    lines.append(empty_line)

            elif self.vert_align is Container.VERT_ALIGN_BOTTOM:
                for _ in range(padding_range):
                    lines.insert(0, empty_line)

        lines.insert(0, _create_border_line(top_left, top_border, top_right))
        lines.append(_create_border_line(bottom_left, bottom_border, bottom_right))

        self._height = len(lines)
        return lines

    def select(self, index: Optional[int] = None) -> None:
        """Select inner object"""

        if index is None:
            if self.selected_index is None:
                raise ValueError(
                    "Cannot select nothing!"
                    + "Either give an argument to select() or set object.selected_index."
                )
            index = self.selected_index

        index = min(max(0, index), len(self._selectables) - 1)

        if (data := self._selectables.get(index)) is None:
            raise IndexError("Container selection index out of range")

        element, inner_index = data
        element.select(inner_index)
        self.selected_index = index

        if self._prev_selected is not None and self._prev_selected is not element:
            self._prev_selected.selected_index = None

        # update self._prev_selected
        _ = self.selected

    def center(
        self, where: Optional[int] = CENTER_BOTH, store: bool = True
    ) -> Container:
        """Center object on given axis, store & reapply if `store`"""

        centerx = where in [Container.CENTER_X, Container.CENTER_BOTH]
        centery = where in [Container.CENTER_Y, Container.CENTER_BOTH]

        if centerx:
            self.posx = (screen_width() - self.width + 2) // 2

        if centery:
            self.posy = (screen_height() - self.height + 2) // 2

        if store:
            self._centered_axis = where

        self._prev_screen = screen_size()

        return self

    def wipe(self) -> None:
        """Wipe characters occupied by the object"""

        with cursor_at(self.pos) as print_here:
            for line in self.get_lines():
                print_here(real_length(line) * " ")

    def print(self) -> None:
        """Print object"""

        if not screen_size() == self._prev_screen:
            clear()
            self.center(self._centered_axis)

        with cursor_at(self.pos) as print_here:
            for line in self.get_lines():
                print_here(line)


class Label(BaseElement):
    """Unselectable text object"""

    ALIGN_LEFT = 0
    ALIGN_CENTER = 1
    ALIGN_RIGHT = 2

    def __init__(self, value: str = "", align: int = ALIGN_CENTER) -> None:
        """Set up object"""

        super().__init__()

        self.value = value
        self.align = align
        self.padding = 0
        self.width = len(value) + self.padding

        self.styles = {
            "value": default_foreground,
        }

    def get_lines(self) -> list[str]:
        """Get lines of object"""

        value_style = self.get_style("value")

        if self.align is Label.ALIGN_CENTER:
            padding = (self.width - real_length(self.value) - self.padding) // 2
            outline = (padding + self.padding + 1) * " " + self.value
            outline += (self.width - real_length(outline) + 1) * " "

            lines = [outline]

        elif self.align is Label.ALIGN_LEFT:
            padding = self.width - real_length(self.value) - self.padding + 1
            lines = [self.padding * " " + self.value + padding * " "]

        elif self.align is Label.ALIGN_RIGHT:
            lines = [
                (self.width - real_length(self.value) - self.padding + 1) * " "
                + self.value
                + self.padding * " "
            ]

        return [value_style(self.depth, line) for line in lines]

    def get_align_string(self) -> str:
        """Get string of align value"""

        if self.align is Label.ALIGN_LEFT:
            align = "ALIGN_LEFT"

        elif self.align is Label.ALIGN_RIGHT:
            align = "ALIGN_RIGHT"

        elif self.align is Label.ALIGN_CENTER:
            align = "ALIGN_CENTER"

        return "Label." + align

    def dbg(self) -> str:
        """Return identifiable information about object"""

        return f'Label(value="{self.value}", align={self.get_align_string()})'


class ListView(BaseElement):
    """Allow selection from a list of options"""

    LAYOUT_HORIZONTAL = 0
    LAYOUT_VERTICAL = 1

    def __init__(
        self,
        options: list[str],
        layout: int = LAYOUT_VERTICAL,
        align: int = Label.ALIGN_CENTER,
        padding: int = 0,
    ) -> None:
        """Initialize object"""

        super().__init__()

        self.padding = padding
        self.options = options
        self.layout = layout
        self.align = align
        self.donor_label = Label(align=self.align)
        self._height = len(self.options)

        self.is_selectable = True
        self.selectables_length = len(options)

        self.styles = {
            "delimiter": default_foreground,
            "value": default_foreground,
            "highlight": default_background,
        }

        self.chars = {"delimiter": ["< ", " >"]}

    def get_lines(self) -> list[str]:
        """Get lines to represent object"""

        lines = []

        value_style = self.get_style("value")
        highlight_style = self.get_style("highlight")
        delimiter_style = self.get_style("delimiter")

        chars = self.get_char("delimiter")
        start, end = [delimiter_style(self.depth, char) for char in chars]

        if self.layout is ListView.LAYOUT_HORIZONTAL:
            pass

        elif self.layout is ListView.LAYOUT_VERTICAL:
            label = self.donor_label
            label.padding = self.padding
            label.width = self.width

            for i, opt in enumerate(self.options):
                value = [start, value_style(self.depth, opt), end]

                # highlight_style needs to be applied to all elements in value
                if i == self.selected_index:
                    label.value = "".join(
                        highlight_style(self.depth, element) for element in value
                    )

                else:
                    label.value = "".join(value)

                lines += label.get_lines()

        self.width = max(real_length(l) for l in lines)

        return lines

    def get_layout_string(self) -> str:
        """Get layout string"""

        if self.layout is ListView.LAYOUT_HORIZONTAL:
            layout = "LAYOUT_HORIZONTAL"
        elif self.layout is ListView.LAYOUT_VERTICAL:
            layout = "LAYOUT_VERTICAL"

        return "ListView." + layout

    def dbg(self) -> str:
        """Return identifiable information about object"""

        return (
            "ListView("
            + f"options={self.options}, "
            + f"layout={self.get_layout_string()}, "
            + f"align={self.donor_label.get_align_string()}"
            + ")"
        )


class Prompt(BaseElement):
    """Selectable object showing a single value with a label"""

    HIGHLIGHT_LEFT = 0
    HIGHLIGHT_RIGHT = 1
    HIGHLIGHT_ALL = 2

    def __init__(
        self, label: str = "", value: str = "", highlight_target: int = HIGHLIGHT_LEFT
    ) -> None:
        """Initialize object"""

        super().__init__()
        self.label = label
        self.value = value
        self.highlight_target = highlight_target

        self.is_selectable = True
        self.selectables_length = 1
        self.styles = {
            "label": default_foreground,
            "value": default_foreground,
            "delimiter": default_foreground,
            "highlight": default_background,
        }

        self.chars = {
            "delimiter": ["< ", " >"],
        }

    def get_lines(self) -> list[str]:
        """Get lines for object"""

        label_style = self.get_style("label")
        value_style = self.get_style("value")
        delimiter_style = self.get_style("delimiter")
        highlight_style = self.get_style("highlight")

        delimiters = self.get_char("delimiter")

        start, end = delimiters
        label = label_style(self.depth, self.label)

        value_list = [
            delimiter_style(self.depth, start),
            value_style(self.depth, self.value),
            delimiter_style(self.depth, end),
        ]

        if self.selected_index is not None:
            if self.highlight_target in [Prompt.HIGHLIGHT_LEFT, Prompt.HIGHLIGHT_ALL]:
                label = highlight_style(self.depth, label)

                if self.highlight_target is Prompt.HIGHLIGHT_LEFT:
                    value = "".join(value_list)

            if self.highlight_target in [Prompt.HIGHLIGHT_RIGHT, Prompt.HIGHLIGHT_ALL]:
                value = "".join(
                    highlight_style(self.depth, item) for item in value_list
                )

        else:
            value = "".join(value_list)

        middle = " " * (self.width - real_length(label + value) + 1)

        if (
            self.selected_index is not None
            and self.highlight_target is Prompt.HIGHLIGHT_ALL
        ):
            middle = highlight_style(self.depth, middle)

        return [label + middle + value]

    def get_highlight_target_string(self) -> str:
        """Get highlight target string"""

        if self.highlight_target == Prompt.HIGHLIGHT_LEFT:
            target = "HIGHLIGHT_LEFT"

        elif self.highlight_target == Prompt.HIGHLIGHT_RIGHT:
            target = "HIGHLIGHT_RIGHT"

        elif self.highlight_target == Prompt.HIGHLIGHT_ALL:
            target = "HIGHLIGHT_ALL"

        return "Prompt." + target

    def dbg(self) -> str:
        """String representation of self"""

        return (
            "Prompt("
            + "label={self.value}, "
            + f"value={self.value}, "
            + f"highlight_target={self.get_highlight_target_string()}"
            + ")"
        )
