import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector
import matplotlib
from PyQt6.QtWidgets import QComboBox, QVBoxLayout, QWidget, QFormLayout, QLabel
matplotlib.use("qtagg")

import numpy as np
from argparse import ArgumentParser
import os
from tqdm import tqdm
from skimage import io, color
from skimage.metrics import structural_similarity as ssim
import time
import traceback

def load_labels(file):
    with open(file, "r") as f: return [line.strip() for line in f]

def load_images(files):
    images = [color.rgb2gray(io.imread(file)) for file in tqdm(files, desc="Loading images")]
    return images

def crop_image(img, roi_coords):
    x1, x2, y1, y2 = roi_coords
    return img[y1:y2,x1:x2]

def group_images_by_similarity(images, file_list, threshold=0.8, roi_coords=(823,366,605,355)):
    num_images = len(images)
    grouped = set()
    groups = []

    # Use tqdm to add a progress bar to the loop
    for i in tqdm(range(num_images), desc="Grouping images"):
        if i in grouped:
            continue  # Skip if already grouped

        # Print the name of the file currently being processed as "i"
        #print(f"Processing image: {file_list[i]}")

        current_group = [i]
        roi_i = crop_image(images[i], roi_coords)  # Crop the ROI for the ith image
        
        for j in range(i + 1, num_images):
            if j not in grouped:
                roi_j = crop_image(images[j], roi_coords)  # Crop the ROI for the jth image
                ssim_index, _ = ssim(roi_i, roi_j, full=True, data_range=1.0)  # Compute SSIM for the ROI
                if ssim_index > threshold:
                    current_group.append(j)
                    grouped.add(j)
        groups.append(current_group)
        grouped.add(i)
    
    return groups

def eval_groups(file_list, images, roi_coords):
    groups = []
    while True:
        threshold = float(input("Threshold: "))
        groups = group_images_by_similarity(images, file_list, threshold, roi_coords)
        print(f"Split up into {len(groups)} groups.")
        print(f"Group sizes: {[len(group) for group in groups]}")
        res = input("Do you want to use this threshold? [y|n] ")


        if res.strip() == "y": break
    return groups

ROI_SELECT = 0
LABEL_SELECT = 1

class State:
    roi_coords = ()
    selector_was_used = False
    label_text = None
    point = None
    menu = ROI_SELECT

    def select_callback(self, eclick, erelease):
        x1, y1 = eclick.xdata, eclick.ydata
        x2, y2 = erelease.xdata, erelease.ydata
        self.selector_was_used = True

    def key_press_callback(self, event):
        if event.key == "enter":
            if self.menu == ROI_SELECT:
                if self.selector_was_used: 
                    self.roi_coords = np.array(selector.extents, dtype=np.int32)
                    self.label_text = combo.currentText()
                    self.menu = LABEL_SELECT
                    plt.close("all")
            elif self.menu == LABEL_SELECT:
                if self.point is not None:
                    plt.close("all")

    def button_press_callback(self, event):
        if event.button == 1:
            x = int(state.roi_coords[0] + event.xdata)
            y = int(state.roi_coords[2] + event.ydata)
            self.point = (x, y)
            print(f"x={x}, y={y}")
            scatter = plt.scatter(event.xdata, event.ydata, color="r")
            fig.canvas.draw()
            scatter.remove()

state = State()

parser = ArgumentParser()
parser.add_argument("image_dir")
parser.add_argument("label_names_file")
args = parser.parse_args()
image_dir = args.image_dir
file_list = [os.path.join(image_dir, file) for file in os.listdir(image_dir) if file.endswith('.jpg')]
images = load_images(file_list)
label_names = load_labels(args.label_names_file)

# select roi region
img = io.imread(file_list[0])
img_height, img_width, _ = img.shape
print(img_width, img_height)
roi_coords = ()
fig, ax = plt.subplots()

manager = plt.get_current_fig_manager()
manager.window.showMaximized()

combo = QComboBox()
combo.addItems(label_names)
central = QWidget()
layout = QVBoxLayout()
label_selector = QWidget()
form_layout = QFormLayout()
form_layout.addRow(QLabel("Label:"), combo)
label_selector.setLayout(form_layout)
layout.addWidget(manager.canvas)
layout.addWidget(label_selector)
central.setLayout(layout)

manager.window.setCentralWidget(central)

ax.imshow(img)
selector = RectangleSelector(ax, state.select_callback, 
                             useblit=True, button=[1,3], 
                             minspanx=5, minspany=5, 
                             spancoords="pixels", drag_from_anywhere=True, 
                             use_data_coordinates=True, interactive=True)

fig.canvas.mpl_connect('key_press_event', state.key_press_callback)

plt.show()
if not state.selector_was_used: exit()

# split up into similar groups
groups = eval_groups(file_list, images, state.roi_coords)

for i, group in enumerate(groups):
    img = io.imread(file_list[group[0]])
    fig = plt.figure()
    fig.suptitle(f"Set label for group {i}. Enter to confirm")
    ax = fig.add_subplot(111)
    ax.imshow(crop_image(img, state.roi_coords))
    fig.canvas.mpl_connect('button_press_event', state.button_press_callback)
    fig.canvas.mpl_connect('key_press_event', state.key_press_callback)
    plt.show()
    dir_name = os.path.basename(os.path.normpath(image_dir))
    with open(f"{dir_name}_labels.csv", "a+") as f:
        for file in np.array(file_list)[group]:
            f.write(f"{state.label_text},{state.point[0]},{state.point[1]},{os.path.basename(file)},{img_width},{img_height}\n")

