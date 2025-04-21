# Georeferencing Annotator
This repository contains a simple georeferencing annotation tool for static persepective videos. The `georef.py` script groups similar ROI regions and assigns them a single point label, to reduce the annotation time. The `label_viewer.py` can be used to load annotation files in the makesense.ai csv export format. You can add single points, edit, or remove them.

Please note that these tools were built over the course of one weekend, by just hacking together some matplotlib and Qt6 functions. So excuse the poor code quality.

## Setup
The code was tested with python 3.12 on MacOS.
```
git clone git@github.com:svenschreiber/georef_annotator.git
cd georef_annotator
pip install -r requirements.txt
```

## Usage: georef.py
Start the tool by passing in the image directory and a file containing the possible labels in seperate lines.

```
python georef.py <image_dir> <label_names_file>
```

The first screen shows a sample image from the specified directory. 
1. Span the ROI region by holding the left mouse button
2. Select the label in the bottom of the window
3. Press ENTER to confirm
4. In the terminal specify a similarity threshold
5. Confirm (y) the threshold or try another (n)
6. For each similarity group a sample image is presented, annotate by left clicking
7. Press ENTER to confirm
8. The annotations for this point label, will automatically be appended to a file named `<video_name>_labels.csv`

### Additional Notes
After the first annotation, the `Use last position` button can be used to copy the pixel location of the last annotation. This can be helpful, when the object is temporarilly occluded and turns out to be difficult to estimate.

Currently, if you are not satisfied with the annotations, the only way to undo them is to go into the .csv file and delete the last lines.

Using the default tools in the navigation bar (e.g. zooming) may break the program.

## Usage: label_viewer.py
Start the tool by passing in the video image directory, the annotations .csv file, and the possible labels file.

```
python label_viewer.py <image_dir> <annotations_file> <label_names_file>
```

- Change the viewed frame by using the `left` and `right` arrow keys.
- Add points by selecting a label in the navigation bar at the top and left clicking on an image location.
- Move points by left clicking on a point and dragging
- Remove a point or change the label of it by right clicking it
- Save the annotations by using the navigation bar icon or by pressing `ctrl+s` (see additional notes, for more info)

### Bulk Label Changer
For cases where you want to change a specific label to another label for a range of frames, the bulk label changer can be used (top right of the window). I use this mainly in situtations where objects are temporarily occluded, so I can change the label to be occluded for a whole range of frames.

### Additional Notes
When saving the annotations, the annotations file is sorted by image name. This changes the order of the `georef.py` output, which just appends annotations at the end of the file.