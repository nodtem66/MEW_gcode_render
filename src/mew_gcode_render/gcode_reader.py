"""
Jirawat Iamsamang
Description: GCode parser based on gcode_reader.js
Last modified: 2026-02-09
"""

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict


@dataclass
class GcodeCommand:
    cmd: str | None
    args: Dict[str, Any] | None
    comment: str | None
    tag: Dict[str, Any] | None

    """Class representing a GCode command."""

    def __init__(self):
        self.cmd = None
        self.args = {}
        self.comment = None
        self.tag = {}


def default_case_transform_fn(key: str) -> str:
    """Default case transformation function (identity)."""
    return key


def parse_comment_tag(
    comment: str, case_transform_fn: Callable[[str], str] = default_case_transform_fn
) -> Dict[str, Any]:
    """
    Parse comment tags.

    Type of command is held within <<< >>>
    Afterwards args are passed
    The arguments are either a value, or a key value pair
    If the args are a single value, then a key value pair is made where the command is the key

    Args:
        comment: The comment string to parse
        case_transform_fn: Function to transform keys (default: identity)

    Returns:
        Dictionary of parsed tag key-value pairs
    """
    if len(comment) > 0:
        split_comment = comment.split(",")
        array_obj = []

        for c in split_comment:
            comment_tag_args = c.lower()
            if ":" in comment_tag_args:
                comment_tag_key_value = comment_tag_args.split(":")
                key = case_transform_fn(comment_tag_key_value[0].strip())

                # Parse to number, if it's a number
                raw_value = comment_tag_key_value[1].strip()
                try:
                    value = float(raw_value)
                    # Convert to int if it's a whole number
                    if value.is_integer():
                        value = int(value)
                except ValueError:
                    value = raw_value

                array_obj.append({key: value})

        # Merge all dictionaries
        result = {}
        for obj in array_obj:
            result.update(obj)
        return result
    return {}


def parse_gcode(gcode: str) -> GcodeCommand:
    """
    Parses a line of GCode and returns an object.

    Expects a single line of gcode.
    Returns an object with a command and a list of arguments.

    Args:
        gcode: A single line of gcode string

    Returns:
        GcodeCommand object with 'cmd', 'args', 'comment', and 'tag' attributes

    Raises:
        TypeError: If gcode is not a string
    """
    # Validate input to be of type "string"
    if not isinstance(gcode, str):
        raise TypeError(f'gcode argument must be of type "string". {gcode} is type "{type(gcode).__name__}"')

    # Constructing a blank gcode object
    gcode_object = GcodeCommand()

    # Split the gcode by the first semicolon it sees
    comment_splits = gcode.split(";")
    gcode_without_comment = comment_splits[0]
    if len(comment_splits) > 1:
        comment = ";".join(comment_splits[1:]).strip()
        gcode_object.comment = comment
        gcode_object.tag = parse_comment_tag(comment)

    # If we can find a command, assign it, otherwise keep the "command" value set to None
    command_regex = r"[GM]\d+"
    command_result = re.search(command_regex, gcode_without_comment.upper())
    if command_result:
        gcode_object.cmd = command_result.group(0)

    # Set the gcode to lower case and remove any G<number> or M<number> commands
    gcode_arg_string = re.sub(r"[gm]\d+", "", gcode_without_comment.lower())

    # Parse each axis for a trailing floating number
    # If no float, treat the axis as a boolean flag
    axes = "abcdefghijklmnopqrstuvwxyz"
    for axis in axes:
        # In most cases we are looking for an axis followed by a number
        axis_and_float_regex = rf"{axis}\s*([+-]?([0-9]*[.])?[0-9]+)"
        result = re.search(axis_and_float_regex, gcode_arg_string)
        if result:
            gcode_object.args[axis] = float(result.group(1))
        # If there is an axis, but no trailing number, pass the axis as a boolean flag
        elif axis in gcode_arg_string:
            gcode_object.args[axis] = True

    return gcode_object
