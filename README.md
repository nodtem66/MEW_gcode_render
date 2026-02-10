# MEW Gcode render

MEW GCode Render converts GCode files from melt electrowrite (MEW) 3D printing into publication-ready 3D visualizations in Blender. The pipeline follows GCode → CSV → Blender, providing a Python program that transforms GCode into CSV point data with support for cylindrical coordinate transformations (useful for tube-based scaffolds), along with prebuilt Blender geometry nodes for efficient rendering of the point trajectories as 3D meshes.

[Examples](./examples/) | [Blender](https://www.blender.org/) | License: [MIT](./LICENSE.md)

## Key features

- **GCode to CSV Conversion**: Directly parse GCode files and export point trajectories to CSV format
- **Cylindrical Coordinate Transformation**: Support for converting Cartesian coordinates to cylindrical coordinates, ideal for MEW scaffold printing on tubular structures
- **Blender Integration**: Prebuilt geometry node templates for seamless import and visualization of CSV point data
- **Efficient Rendering**: Node-based workflow enables fast real-time visualization and animation of print paths
- **Command-line Interface**: Simple CLI for batch processing and automation of GCode conversions

## How to use the software

### Step 1: Convert GCode to CSV (Python)

Run the Python script to convert your GCode file to CSV format:

```sh
python -m mew_gcode_render file.gcode -y u -d 3 -r 10
```

**Parameters:**
- `file.gcode`: Input GCode file
- `-y u`: Map U symbol in `file.gcode` to Y axis
- `-d 3`: Diameter parameter for tube
- `-r 10`: Curve resolution

This generates a CSV file with x, y, z coordinates of the print path.

### Step 2: Visualize in Blender

#### Setup (one-time):

1. **Add geometry node template to asset library**
   - Open Blender
   - Edit → Preferences → File Paths → Asset Libraries
   - Add the folder `./blender_templates`

2. **Install CSV Importer extension**
   - Edit → Preferences → Get Extensions
   - Search for "CSV Importer" and install

#### Import and render:

3. **Import the CSV file and apply geometry nodes**
   - File → Import → CSV → Select your generated CSV file
   - Select the imported object
   - Open the Geometry Nodes panel → Click "New"
   - In the Asset Browser, navigate to `blender_templates`
   - Drag `CSV Paths to Mesh` node into the geometry node tree
   - Connect it between the input and output nodes

4. **Visualize the result**
   - Press Space to play the animation and visualize the print path as a 3D mesh  