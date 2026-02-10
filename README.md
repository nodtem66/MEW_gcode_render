# MEW Gcode render

This repository contains scripts and a blender template for rendering MEW scaffold design from Gcode.  

## Python part

The python script

## Blender part

1) Add geometry node template to asset library 
 - Open Blender
 - Edit > Preferences > File Path > Asset Libraries
 - Add folder `./blender_templates`

2) Install CSV Importer
 - Edit > Preferences > Get Extensions > CSV Importer > Install 

3) Import CSV file
 - File > Import > CSV > Select the csv file containing x,y,z positions.
 - Select the imported object
 - Open Geometry node > New 
 - Asset browser > `blender_templates` > Drag `CSV Paths to Mesh` to the link between input group and output.
 - Please space to see the animation.  