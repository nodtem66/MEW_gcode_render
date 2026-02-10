import unittest

from mew_gcode_render.gcode_reader import GcodeCommand
from mew_gcode_render.geometry_parser import GeometryParser

class TestGeometryParser(unittest.TestCase):
    def test_process_move_command(self):
        gcode_command = GcodeCommand()
        gcode_command.cmd = "G1"
        gcode_command.args = {"x": 10, "y": 20}

        parser = GeometryParser()
        parser.process([gcode_command])
        self.assertEqual(len(parser.geometry), 1)
        self.assertEqual(parser.geometry[0].type, "line")
        self.assertEqual(parser.geometry[0].start, [0, 0, 0])
        self.assertEqual(parser.geometry[0].end, [10, 20, 0])
        self.assertEqual(parser.geometry[0].feedrate, 100)

    def test_process_arc_command(self):
        gcode_command = GcodeCommand()
        gcode_command.cmd = "G2"
        gcode_command.args = {"x": 10, "y": 20, "i": 5, "j": 5}

        parser = GeometryParser()
        parser.process([gcode_command])
        self.assertEqual(len(parser.geometry), 1)
        self.assertEqual(parser.geometry[0].type, "arc")
        self.assertEqual(parser.geometry[0].dir, "cw")
        self.assertEqual(parser.geometry[0].start, [0, 0, 0])
        self.assertEqual(parser.geometry[0].end, [10, 20, 0])
        self.assertEqual(parser.geometry[0].center, [5, 5])
        self.assertEqual(parser.geometry[0].feedrate, 100)

if __name__ == '__main__':
    unittest.main()
