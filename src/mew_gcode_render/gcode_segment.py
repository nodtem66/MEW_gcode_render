import math
import os

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from typing import Any

from libs.gcode_reader import GcodeParser
from tqdm import tqdm

cos_d = lambda degree : math.cos(degree * math.pi / 180.)
sin_d = lambda degree : math.sin(degree * math.pi / 180.)
rotational_matrix = lambda degree : np.array([[cos_d(degree), -sin_d(degree)], [sin_d(degree), cos_d(degree)]])
rotational_matrix_radian = lambda radian : np.array([[math.cos(radian), -math.sin(radian)], [math.sin(radian), math.cos(radian)]])
is_numpy_array = lambda x : type(x).__module__ == np.__name__

@dataclass
class GcodeSegment:
  position: NDArray[Any] | list[Any]
  velocity: NDArray[Any] | list[Any]
  time: NDArray[Any] | list[Any]
  fline_position_map: NDArray[Any] | list[int]

  def get_data(self):
    return self.position, self.velocity, self.time
  
  def get_xyz(self, cylinder_diameter:float = 0.0):
    self.position = np.array(self.position)
    assert self.position.shape[1] >= 2, f'Position shape {self.position.shape} is invalid'
    if cylinder_diameter > 0:
      # convert 2D xy coordinate to 3d cylindrical coordinate
      radius = cylinder_diameter / 2
      p = radius
      φ = self.position[:, 1]/radius
      z = self.position[:, 0]
      # convert 3d cylindrical coordinate to 3d cartesian coordinate
      x = p * np.cos(φ)
      y = p * np.sin(φ)
      return x, y, z
    elif self.position.shape[1] == 3:
      return self.position[:,0], self.position[:,1], self.position[:,2]
    else:
      return self.position[:,0], self.position[:,1], np.zeros(self.position.shape[0])
  
  def __init__(self, filename:str = '', **kwargs):
    """
    Parse GCODE into line and speed segments

    Parameters
    ----------
    filename : str
      Name of gcode file
    **kwargs : dict, optional
      Extra arguments
      {'default_speed': 200}
      {'arc_segment': 100}
      {'progress_bar': False}

    Returns
    -------
    positions : list
      list of points
    velocities : list
      list of speeds
    times : list
      list of times
    """

    if not os.path.exists(filename):
      raise FileNotFoundError(f'{filename} did not exist')
    
    # Variables
    # position mode
    POSITION_ABSOLUTE = 0
    POSITION_RELATIVE = 1
    position_mode = POSITION_ABSOLUTE
    
    # Parameters
    DEFAULT_SPEED = kwargs.get('default_speed', 200) #mm/min
    ARC_SEGMENTS = kwargs.get('arc_segments', 100) # the number of arc segments
    show_progress_bar = kwargs.get('progress_bar', False) # show progress bar or not
    X_AXIS = kwargs.get('x_axis', 'X') # name of the first axis
    Y_AXIS = kwargs.get('y_axis', 'auto') # name of the 2nd axis
    Z_AXIS = kwargs.get('z_axis', 'Z') # name of the 3rd axis
    
    # vertices
    positions = [np.array([0,0,0], dtype='double')] #mm
    velocities = [] #mm/min
    times = [] ##min
    EPS = np.finfo('double').eps * 10

    # Auto detect the 2nd axis
    if Y_AXIS == 'auto':
      axis_names = get_axis_names(filename)
      assert len(axis_names.keys()) >= 2, f'Axis names {axis_names} is invalid'
      axis_names = list(axis_names.keys())
      if X_AXIS in axis_names:
        axis_names.remove(X_AXIS)
      if Z_AXIS in axis_names:
        axis_names.remove(Z_AXIS)
      assert len(axis_names) > 0, f'Axis names {axis_names} is invalid'
      Y_AXIS = axis_names[0]
      print(f'Auto detect {Y_AXIS} as Y axis')
    
    num_lines = sum(1 for _ in open(filename, 'rb'))
    self.fline_position_map = []
    with open(filename, 'r') as f:

      for file_line in tqdm(f, desc='Parse GCODE', disable=not show_progress_bar, total=num_lines):
        parsed_gcode = GcodeParser(file_line, include_comments=False)
        self.fline_position_map.append(len(positions))
        if len(parsed_gcode.lines) == 0:
          continue
        for line in parsed_gcode.lines:
          command = line.command
          if command == ('G', 90):
            position_mode = POSITION_ABSOLUTE
          elif command == ('G', 91):
            position_mode = POSITION_RELATIVE
          # IF G0 G1 G2 G3
          is_linear_move = command == ('G', 0) or command == ('G', 1)
          is_arc_move = command == ('G', 2) or command == ('G', 3)
          is_counterclockwise = command == ('G', 3)
          if is_linear_move or is_arc_move:
            prev_pos = positions[-1].copy()
            new_pos = positions[-1].copy()
            #print(f'move {line.params} ' + ('R' if position_mode else 'A'))

            # Feed rate parsing
            speed = DEFAULT_SPEED
            if line.get_param('F') is not None:
              speed = line.get_param('F', default=DEFAULT_SPEED)
              DEFAULT_SPEED = speed
              # Case: G0 Fn and G1 Fn
              # set the default speed
              if is_linear_move and line.get_param(X_AXIS) is None and line.get_param(Y_AXIS) is None and line.get_param(Z_AXIS) is None and line.get_param('E') is None:
                continue
            
            # Position parsing
            if position_mode == POSITION_ABSOLUTE:
              if line.get_param(X_AXIS) is not None:
                new_pos[0] = line.get_param(X_AXIS)
              if line.get_param(Y_AXIS) is not None:
                new_pos[1] = line.get_param(Y_AXIS)
              if line.get_param(Z_AXIS) is not None:
                new_pos[2] = line.get_param(Z_AXIS)

            if position_mode == POSITION_RELATIVE:
              if line.get_param(X_AXIS) is not None:
                new_pos[0] += line.get_param(X_AXIS)
              if line.get_param(Y_AXIS) is not None:
                new_pos[1] += line.get_param(Y_AXIS)
              if line.get_param(Z_AXIS) is not None:
                new_pos[2] += line.get_param(Z_AXIS)
            
            if is_linear_move:
              velocities.append(speed)
              positions.append(np.array(new_pos, dtype='double'))
              _distance = np.linalg.norm(new_pos - prev_pos)
              _speed = velocities[-1]
              if _distance < EPS:
                # Do nothing and remove the useless movement
                velocities.pop()
                positions.pop()
                continue
              elif _speed > EPS:
                times.append(_distance / _speed)
              else:
                raise ValueError(f'Distance {_distance} or Speed {_speed} is invalid')
            elif is_arc_move:
              i_pos = line.get_param('I') 
              j_pos = line.get_param('J')
              radius = line.get_param('R')
              if i_pos is not None and j_pos is not None:
                center_pos = prev_pos.copy()
                center_pos[0] += i_pos
                center_pos[1] += j_pos
              elif radius is not None:
                # When R is specified
                # There is 2 way to draw an arc: large arc sweep or small arc sweep
                # https://developer.mozilla.org/en-US/docs/Web/SVG/Tutorial/Paths#curve_commands
                # Then I decided to follow the Marlin document to chose small arc sweep
                center_pos = prev_pos.copy()
                vector_S = new_pos - prev_pos
                norm_S = np.linalg.norm(vector_S)
                assert norm_S > EPS
                unit_S = vector_S / norm_S
                unit_S_rotated = unit_S.copy()
                middle_point = prev_pos + 0.5 * norm_S * unit_S
                rot_matrix = rotational_matrix(90) if is_counterclockwise else rotational_matrix(-90)
                unit_S_rotated[:2] = rot_matrix @ unit_S[:2]
                norm_S_rotated = np.sqrt(radius ** 2 - (0.5 * norm_S)**2)
                center_pos = middle_point + unit_S_rotated * norm_S_rotated
              else:
                raise ValueError(f'I, J, or R is required in GCODE:{line}')
              
              # correct the new position
              if radius is None:
                radius = np.linalg.norm(prev_pos - center_pos)
              if np.linalg.norm(new_pos - center_pos) - radius > EPS:
                vector_S = new_pos - center_pos
                norm_S = np.linalg.norm(new_pos - center_pos)
                unit_S = vector_S / norm_S
                assert norm_S > EPS
                new_pos = center_pos + unit_S * radius

              #print(f'{line}:\n\t{prev_pos}->{new_pos} C{center_pos}')
              # TODO: change to this implement
              # https://github.com/mrdoob/three.js/blob/master/src/extras/curves/EllipseCurve.js
              vector_1 = prev_pos - center_pos
              vector_2 = new_pos - center_pos
              cross_12 = np.cross(vector_1[:2], vector_2[:2])
              #print(f'\tv1: {vector_1}, v2: {vector_2}, cross12: {cross_12}')

              # cross product will be >= 0
              # if cross product == 0, then angle is 180 or 360 degrees
              if np.abs(cross_12) < EPS:
                if np.linalg.norm(new_pos - prev_pos) < EPS:
                  angle = 2 * np.pi 
                else:
                  angle = np.pi
              else:
                # v1.v2 = |v1||v2| cos(theta)
                # theta = v1.v2 / |v1||v2|
                dot_12 = np.dot(vector_1, vector_2)
                angle = np.arctan2(cross_12, dot_12)
                #print(f'\traw theta: {angle*180/np.pi}')
                is_ccw_negative_angle = is_counterclockwise and angle < 0
                is_cw_positive_angle = (not is_counterclockwise) and angle > 0
                if is_ccw_negative_angle or is_cw_positive_angle:
                  if angle > 0:
                    angle = 2 * np.pi - angle
                  else:
                    angle = -(2 * np.pi + angle)

              #print(f'\tAngle: {angle*180/np.pi} deg')
              angle_steps = angle / ARC_SEGMENTS * np.arange(1, ARC_SEGMENTS+1).astype('double')
              #print(angle_steps)
              assert speed is not None
              for _r in angle_steps:
                _pos = center_pos.copy()
                _pos[:2] += rotational_matrix_radian(-_r) @ (prev_pos - center_pos)[:2]
                _distance = np.linalg.norm(_pos - positions[-1])
                velocities.append(speed)
                positions.append(_pos)
                if _distance < EPS:
                  print(_distance)
                  times.append(0)
                elif speed > EPS:
                  times.append(_distance / speed)
                else:
                  raise ValueError(f'Distance {_distance} or Speed {speed} is invalid')
              #print(f'\t{positions[-1]} {new_pos}')

              # Generate an arc from two points on circle with a center point
                
          # END IF G0 G1 G2 G3

          # IF G4 Dwell 
          elif command == ('G', 4):
            new_pos = list(positions[-1])
            dwell_msec = 0
            if line.get_param('P') is not None:
              _p = line.get_param('P', return_type=float)
              assert isinstance(_p, (int, float))
              dwell_msec += _p
            if line.get_param('S') is not None:
              _p = line.get_param('S', return_type=float)
              assert isinstance(_p, (int, float))
              dwell_msec += _p*1000
            if dwell_msec > 0:
              positions.append(np.array(new_pos, dtype='double'))
              velocities.append(0)
              # Since the unit of times is minute, dwell_msec is converted into minute
              times.append(dwell_msec/1000.0/60.0)
        # END Loop through GCODEPARSER lines
      # END Loop through GCODE lines
    # END Loop through GCODE files
    if len(positions) > len(velocities):
      velocities.append(0)
    
    if len(positions) > len(times):
      times.append(0)
    
    self.position = positions
    self.velocity = velocities
    self.time = times

  def linespace(self, **kwargs):
    """
    Create small steps from the parsed GCODE lines
    time_resolution : int
      A number to calculate time_step := minimum time / time_resolution.
      A higher value is more precision but more time to compute.
    """
    self.position, self.velocity, self.time = create_linespace(self.position, self.velocity, self.time, **kwargs)

  @classmethod
  def parse_gcode(cls, gcode_file:str, **kwargs):
    """
    Parse a GCODE file into a list of lines

    Parameters
    ----------
    gcode_file : str
      A path to a GCODE file
    verbose : bool
      A flag to print out debugging information
    """
    s = cls(gcode_file, **kwargs)
    if 'return_file_line' in kwargs and kwargs['return_file_line']:
      return s.position, s.velocity, s.time, s.fline_position_map
    return s.get_data()

def create_linespace(lines, speeds, times = [],
  time_resolution:int|None=None,
  time_step:float=0.1,
  eps = np.finfo('double').eps,
  verbose:bool=False,
  **kwargs):
  """
  Create small steps from the parsed GCODE lines

  Parameters
  ----------
  time_resolution : double
    A number to calculate time_step := minimum time / time_resolution.
    A higher value is more precision but more time to compute.
  time_step : double (Not recommended)
    A higher value is more precision but more time to compute.
  """

  _np = []
  _v_np = []
  _t_np = []

  assert hasattr(lines, '__len__'), 'lines must be a list or numpy.array'
  assert hasattr(speeds, '__len__'), 'speeds must be a list or numpy.array'
  assert hasattr(times, '__len__'), 'times must be a list or numpy.array'

  if not is_numpy_array(lines):
    lines = np.array(lines, dtype='double')
    speeds = np.array(speeds, dtype='double')
    times = np.array(times, dtype='double')

  total_number_of_positions = len(lines)

  # Find the minimum time step from times
  assert len(lines) == len(speeds), 'Length of lines must = Length of speeds'
  
  if times is None or len(times) != len(lines):
    times = np.zeros_like(speeds, dtype='double')
    for current_pos in range(total_number_of_positions):
      if current_pos + 1 >= total_number_of_positions:
        break
      _distance = np.linalg.norm(lines[current_pos+1] - lines[current_pos])
      if speeds[current_pos] > eps:
        times[current_pos] = _distance / speeds[current_pos]
  
  assert len(lines) == len(times), 'Length of lines must = Length of times'

  if time_resolution is not None:
    min_times = np.min(times[times > 0])
    t_step = 10 ** np.ceil(np.log10(min_times/time_resolution))
  else:
    t_step = time_step

  assert t_step > 0, f't_step = {t_step} must > 0'

  if verbose:
    print(f'  t_step: {t_step}')
    
  for current_pos in range(total_number_of_positions):
    next_pos = current_pos+1
    if next_pos >= total_number_of_positions:
      break
    vector_S = lines[next_pos] - lines[current_pos]
    norm_S = np.linalg.norm(vector_S)

    if verbose:
      print(times[current_pos])
    if times[current_pos] < eps:
      continue
    number_steps = times[current_pos] / t_step
    assert number_steps > eps, f'numer_steps = {number_steps} must > 0 in pos{current_pos}'
    
    number_steps_floor = np.floor(number_steps)
    number_steps_ceil = int(np.ceil(number_steps))
    number_steps_decimal = number_steps - number_steps_floor

    if norm_S > 1e-9:
      unit_S = vector_S / norm_S
    else:
      unit_S = np.zeros_like(vector_S, dtype='double')

    _v = speeds[current_pos] * unit_S
    _v_steps = np.ones((number_steps_ceil, 1), dtype='double') * _v
    step_ranges = np.arange(0, number_steps_ceil).reshape(-1,1).astype('double')

    assert len(step_ranges) > 0, 'Length step_ranges must > 0'
    # step_ranges is 0,1,2,3,...,N
    if number_steps_decimal > eps:
      # but the last step will be N-1 + number_steps_decimal or N - (1-number_steps_decimal)
      step_ranges[-1] -= (1-number_steps_decimal)
    # _t_steps = 0, t_step, 2*t_step, 3*t_step, ...
    _t_steps = step_ranges * t_step

    # _t = t_step, t_step, t_step, ...
    _t = np.ones_like(_t_steps, dtype='double')
    if number_steps_decimal > eps:
      _t[-1] = number_steps_decimal
    _t = _t * t_step


    # s = s0 + v * delta_t
    #print(f'{lines[current_pos]} + {step_ranges[-1]} * {t_step} @ {_v}')
    #print(f'{lines[current_pos].shape} + {_t_steps.shape} * {_v.shape}')
    _s_steps = lines[current_pos] + _t_steps * _v

    assert _s_steps.shape[0] == number_steps_ceil, f'len(_s_steps): {_s_steps.shape[0]} != {number_steps_ceil}'
    assert _v_steps.shape[0] == _s_steps.shape[0]
    assert _t_steps.shape[0] == _s_steps.shape[0]

    _np.append(_s_steps)
    _v_np.append(_v_steps)
    _t_np.append(_t)

    #print(f'{_s_steps[0]} -> {_s_steps[-1]}')

  _np.append(lines[-1])
  _v_np.append([0,0,0])
  _t_np.append(0)

  if verbose:
    print(f'  num_points: {len(_v_np)}')
  NP = np.vstack(_np)
  V_NP = np.vstack(_v_np)
  T_NP = np.vstack(_t_np)
  return NP, V_NP, T_NP

def get_axis_names(filename:str = '', read_limit:int = 1000):
  axis_dict = {}
  if not os.path.exists(filename):
    raise FileNotFoundError(f'{filename} did not exist')
  
  with open(filename, 'r') as f:
    for line in f:
      parsed_line = GcodeParser(line)
      if len(parsed_line.lines) == 0:
        continue
      for param in parsed_line.lines[0].params.keys():
        if param not in ['F', 'I', 'J', 'S', 'P']:
          count = axis_dict.get(param, 0)
          axis_dict[param] = count + 1
      read_limit -= 1
      if read_limit <= 0:
        break
  return axis_dict