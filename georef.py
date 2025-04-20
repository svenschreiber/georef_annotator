import matplotlib
import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector
matplotlib.use("qtagg")

from PyQt6.QtWidgets import QComboBox, QVBoxLayout, QWidget, QFormLayout, QLabel, QPushButton

from skimage import io, color
from skimage.metrics import structural_similarity as ssim

import numpy as np
from argparse import ArgumentParser
import os
from tqdm import tqdm
import time
import traceback

# Crosshair cursor from this tutorial: https://matplotlib.org/stable/gallery/event_handling/cursor_demo.html
class BlittedCursor:
    """
    A cross-hair cursor using blitting for faster redraw.
    """
    def __init__(self, ax):
        self.ax = ax
        self.background = None
        self.horizontal_line = ax.axhline(color='gray', lw=0.8, ls='--')
        self.vertical_line = ax.axvline(color='gray', lw=0.8, ls='--')
        self._creating_background = False
        ax.figure.canvas.mpl_connect('draw_event', self.on_draw)

    def on_draw(self, event):
        self.create_new_background()

    def set_cross_hair_visible(self, visible):
        need_redraw = self.horizontal_line.get_visible() != visible
        self.horizontal_line.set_visible(visible)
        self.vertical_line.set_visible(visible)
        return need_redraw

    def create_new_background(self):
        if self._creating_background:
            # discard calls triggered from within this function
            return
        self._creating_background = True
        self.set_cross_hair_visible(False)
        self.ax.figure.canvas.draw()
        self.background = self.ax.figure.canvas.copy_from_bbox(self.ax.bbox)
        self.set_cross_hair_visible(True)
        self._creating_background = False

    def on_mouse_move(self, event):
        if self.background is None:
            self.create_new_background()
        if not event.inaxes:
            need_redraw = self.set_cross_hair_visible(False)
            if need_redraw:
                self.ax.figure.canvas.restore_region(self.background)
                self.ax.figure.canvas.blit(self.ax.bbox)
        else:
            self.set_cross_hair_visible(True)
            # update the line positions
            x, y = event.xdata, event.ydata
            self.horizontal_line.set_ydata([y])
            self.vertical_line.set_xdata([x])

            self.ax.figure.canvas.restore_region(self.background)
            self.ax.draw_artist(self.horizontal_line)
            self.ax.draw_artist(self.vertical_line)
            self.ax.figure.canvas.blit(self.ax.bbox)

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

def draw_point(fig, x, y):
    scatter = plt.scatter(x, y, color="r")
    fig.canvas.draw()
    scatter.remove()

def draw_last_point():
    draw_point(fig, last_pos[0], last_pos[1])

def mouse_move(event):
    if event.inaxes:
        hline.set_ydata(event.ydata)
        vline.set_xdata(event.xdata)
        fig.canvas.draw_idle()

class State:
    roi_coords = ()
    label_text = None
    point = None
    menu = ROI_SELECT

    def select_callback(self, eclick, erelease):
        x1, y1 = eclick.xdata, eclick.ydata
        x2, y2 = erelease.xdata, erelease.ydata

    def key_press_callback(self, event):
        if event.key == "enter":
            if self.menu == ROI_SELECT:
                if selector._selection_artist.get_visible(): 
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
            draw_point(fig, event.xdata, event.ydata)


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
while True:
    state = State()
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
    if not selector._selection_artist.get_visible(): exit()

    # split up into similar groups
    print(f"Selected ROI region {state.roi_coords} with label '{state.label_text}'")
    groups = eval_groups(file_list, images, state.roi_coords)

    last_pos = None
    for i, group in enumerate(groups):
        img = io.imread(file_list[group[0]])
        fig = plt.figure()
        fig.suptitle(f"Set label for group {i}. Enter to confirm")
        ax = fig.add_subplot(111)
        ax.imshow(crop_image(img, state.roi_coords))
        fig.canvas.mpl_connect('button_press_event', state.button_press_callback)
        fig.canvas.mpl_connect('key_press_event', state.key_press_callback)

        blitted_cursor = BlittedCursor(ax)
        fig.canvas.mpl_connect('motion_notify_event', blitted_cursor.on_mouse_move)

        manager = plt.get_current_fig_manager()
        central = QWidget()
        layout = QVBoxLayout()
        button = QPushButton("Use last position")
        button.clicked.connect(draw_last_point)
        if last_pos is None: button.setEnabled(False)
        layout.addWidget(manager.canvas)
        layout.addWidget(button)
        central.setLayout(layout)
        manager.window.setCentralWidget(central)

        plt.show()
        last_pos = (state.point[0] - state.roi_coords[0], state.point[1] - state.roi_coords[2])
        dir_name = os.path.basename(os.path.normpath(image_dir))
        with open(f"{dir_name}_labels.csv", "a+") as f:
            for file in np.array(file_list)[group]:
                f.write(f"{state.label_text},{state.point[0]},{state.point[1]},{os.path.basename(file)},{img_width},{img_height}\n")

