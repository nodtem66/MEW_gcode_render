import unittest
import math
from mew_gcode_render.cli import transformToCylindrical
from mew_gcode_render.gcode_reader import GcodeCommand
from mew_gcode_render.geometry_parser import GeometryParser

class TestCylindricalTransform(unittest.TestCase):
    def test_simple_rotation(self):
        diameter = 3
        gcodes = [
            "G91",
            f"G1 X0 Y{math.pi*diameter}",
            "G1 X0 Y1",
        ]
        gcode_commands = [GcodeCommand.parse(g) for g in gcodes]
        geometry_parser = GeometryParser()
        geometry_parser.process(gcode_commands)

        for curve in geometry_parser.geometry:
            print(curve)
            points = curve.compute_points(20)
            transformed_points = [transformToCylindrical(p, diameter, "x") for p in points]
            for p, tp in zip(points, transformed_points):
                print(f"Original: {p}, Transformed: {tp}")

if __name__ == '__main__': # pragma: no cover
    unittest.main()