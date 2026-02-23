from dataclasses import dataclass, field
from enum import Enum
import math

from mew_gcode_render.gcode_reader import GcodeCommand


class PositionSystem(Enum):
    ABSOLUTE = 0
    RELATIVE = 1


def linspace(start: float, stop: float, num: int = 10) -> list[float]:
    """
    linspace(start, stop, num) returns num evenly spaced samples, calculated over the interval [start, stop].
    If num is 1, the function returns an array containing only the start value. If num is 0, the function returns an empty array.
    Args:
        - start: The starting value of the sequence.
        - stop: The end value of the sequence.
        - num: The number of samples to generate. Must be a non-negative integer. Default is 10.
    Return:
        An array of num evenly spaced samples, calculated over the interval [start, stop].
    Example:
    >>> linspace(0, 10, 5)
    array([ 0.,  2.5,  5.,  7.5, 10.])
    """
    match num:
        case _ if num < 0:
            raise ValueError("num must be a non-negative integer")
        case 0:
            return []
        case 1:
            return [start]
        case _:
            step = (stop - start) / (num - 1)
            return [start + i * step for i in range(num)]


@dataclass
class Curve:
    """Class representing a curve segment."""

    start: list[float] = field(default_factory=list)
    end: list[float] = field(default_factory=list)
    feedrate: float = 100

    def compute_points(self, num_points=20):
        """
        Get a list of points along the curve.
        Parameters:
            num_points: number of points to generate along the curve (default: 20)
        Returns:
            list of points along the curve
        """
        raise NotImplementedError("compute_points must be implemented in subclasses")


@dataclass
class Line(Curve):
    def compute_points(self, num_points=20):
        x_points = linspace(self.start[0], self.end[0], num_points)
        y_points = linspace(self.start[1], self.end[1], num_points)
        if len(self.start) > 2 and len(self.end) > 2:
            z_points = linspace(self.start[2], self.end[2], num_points)
            return [[x, y, z] for x, y, z in zip(x_points, y_points, z_points)]
        return [[x, y, 0] for x, y in zip(x_points, y_points)]


@dataclass
class Arc(Curve):
    dir: str = "cw"
    center: list[float] = field(default_factory=list)

    def compute_points(self, num_points=20):
        center_x, center_y = self.center
        radius = math.sqrt((self.start[0] - center_x) ** 2 + (self.start[1] - center_y) ** 2)
        start_angle = math.atan2(self.start[1] - center_y, self.start[0] - center_x)
        end_angle = math.atan2(self.end[1] - center_y, self.end[0] - center_x)

        angleCalc = end_angle - start_angle
        isCw = self.dir == "cw"
        if isCw and angleCalc > 0:
            angleCalc -= 2 * math.pi
        elif not isCw and angleCalc < 0:
            angleCalc += 2 * math.pi

        if abs(angleCalc) < 1e-3:
            angleCalc = 2 * math.pi if not isCw else -2 * math.pi

        points = []
        for i in range(num_points + 1):
            t = i / num_points
            angle = start_angle + t * angleCalc
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            if len(self.start) > 2 and len(self.end) > 2:
                z = self.start[2] + t * (self.end[2] - self.start[2])
            else:
                z = 0
            points.append([x, y, z])
        return points


class GeometryParser:
    """Class to parse GCode commands into geometry."""

    position: dict[str, float]
    positionSystem: PositionSystem
    feedrate: float
    geometry: list[Curve]
    x_axis: str
    y_axis: str
    z_axis: str
    lineCount: int

    def __init__(
        self,
        x_axis: str = "x",
        y_axis: str = "y",
        z_axis: str = "z",
        positionSystem: PositionSystem = PositionSystem.ABSOLUTE,
        feedrate: float = 100,
    ):
        """
        Initializes the GeometryParser with default values.
        Parameters:
        x_axis: The key to use for the X axis (default: "x")
        y_axis: The key to use for the Y axis (default: "y")
        z_axis: The key to use for the Z axis (default: "z")
        positionSystem: The initial position system (default: PositionSystem.ABSOLUTE)
        feedrate: The initial feedrate (default: 100)
        """
        self.position = {"x": 0, "y": 0, "z": 0}
        self.positionSystem = positionSystem
        self.feedrate = feedrate
        self.geometry = []
        self.cursorPosition = []
        self.x_axis = x_axis.lower()
        self.y_axis = y_axis.lower()
        self.z_axis = z_axis.lower()
        self.lineCount = 0

    def process(self, gcode_array: list[GcodeCommand]):
        """Process an array of gcode commands."""
        for x in gcode_array:
            self.lineCount += 1
            if x.cmd and hasattr(self, x.cmd):
                method = getattr(self, x.cmd)
                method(x.args)
            if x.tag:
                self.processComment(x.tag)

    def isRelativePosition(self):
        return self.positionSystem == PositionSystem.RELATIVE

    def isAbsolutePosition(self):
        return self.positionSystem == PositionSystem.ABSOLUTE

    def processComment(self, tag):
        for key, val in tag.items():
            if key == "CTS":
                self.feedrate = val

    def getAxisValue(self, args, axis):
        axis_attr = axis + "_axis"
        if hasattr(self, axis_attr):
            axis_key = getattr(self, axis_attr)
            if axis_key in args:
                return args[axis_key]
        if axis in args:
            return args[axis]
        return None

    def getAllAxesValues(self, args):
        vals = {"x": 0, "y": 0, "z": 0}
        if self.isAbsolutePosition():
            val_x = self.getAxisValue(args, "x")
            val_y = self.getAxisValue(args, "y")
            val_z = self.getAxisValue(args, "z")
            vals["x"] = val_x if val_x is not None else self.position["x"]
            vals["y"] = val_y if val_y is not None else self.position["y"]
            vals["z"] = val_z if val_z is not None else self.position["z"]
        elif self.isRelativePosition():
            vals["x"] = self.position["x"] + (self.getAxisValue(args, "x") or 0)
            vals["y"] = self.position["y"] + (self.getAxisValue(args, "y") or 0)
            vals["z"] = self.position["z"] + (self.getAxisValue(args, "z") or 0)
        return vals

    def G0(self, args):
        prev_position = self.position.copy()
        vals = self.getAllAxesValues(args)
        self.position["x"] = vals["x"]
        self.position["y"] = vals["y"]
        self.position["z"] = vals["z"]

        self.geometry.append(
            Line(
                start=[prev_position["x"], prev_position["y"], prev_position["z"]],
                end=[self.position["x"], self.position["y"], self.position["z"]],
                feedrate=args.get("f", self.feedrate),
            )
        )

    def G1(self, args):
        self.G0(args)

    def G2(self, args, dir="cw"):
        prev_position = self.position.copy()
        vals = self.getAllAxesValues(args)
        self.position["x"] = vals["x"]
        self.position["y"] = vals["y"]
        self.position["z"] = vals["z"]

        center_x = args.get("i", 0)
        center_y = args.get("j", 0)
        if self.isRelativePosition():
            center_x += prev_position["x"]
            center_y += prev_position["y"]

        self.geometry.append(
            Arc(
                start=[prev_position["x"], prev_position["y"], prev_position["z"]],
                end=[self.position["x"], self.position["y"], self.position["z"]],
                feedrate=args.get("f", self.feedrate),
                dir=dir,
                center=[center_x, center_y],
            )
        )

    def G3(self, args):
        self.G2(args, "ccw")

    def G90(self, _):
        self.positionSystem = PositionSystem.ABSOLUTE

    def G91(self, _):
        self.positionSystem = PositionSystem.RELATIVE
