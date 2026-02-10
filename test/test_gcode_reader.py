import unittest

from mew_gcode_render.gcode_reader import create_gcode_object, parse_gcode

class TestGCodeReader(unittest.TestCase):
    def test_create_gcode_object(self):
        gcode_obj = create_gcode_object()
        self.assertIsInstance(gcode_obj, dict)
        self.assertIn('cmd', gcode_obj)
        self.assertIsInstance(gcode_obj['args'], dict)

    def test_gcode_to_json(self):
        gcode_line = "G1 X10 Y20 Z30 ; This is a comment, tag1:100, tag2:200"
        expected_output = {
            'cmd': 'G1',
            'args': {'x': 10.0, 'y': 20.0, 'z': 30.0},
            'comment': 'This is a comment, tag1:100, tag2:200',
            'tag': {'tag1': 100, 'tag2': 200}
        }
        result = parse_gcode(gcode_line)
        self.assertEqual(result['cmd'], expected_output['cmd'])
        self.assertEqual(result['args'], expected_output['args'])
        self.assertEqual(result['comment'], expected_output['comment'])
        self.assertEqual(result['tag'], expected_output['tag'])

    def test_unknown_gcode_command(self):
        gcode_line = "H99 X10 Y20 Z30"
        result = parse_gcode(gcode_line)
        self.assertIsNone(result['cmd'])
        self.assertEqual(result['args'], {'h': 99.0, 'x': 10.0, 'y': 20.0, 'z': 30.0})


if __name__ == '__main__':
    unittest.main()