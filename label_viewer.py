import matplotlib.pyplot as plt
from argparse import ArgumentParser
from skimage.io import imread_collection
import matplotlib
matplotlib.use("qtagg")
import os
import pandas as pd

def load_annotations(file):
    df = pd.read_csv("DJI_20250224151119_0071_D_labels.csv", sep=",", header=None)
    df.columns = ['label', 'x', 'y', 'filename', 'width', 'height']
    grouped = df.groupby('filename').apply(lambda g: list(zip(g['x'], g['y'])), include_groups=False)
    return grouped.to_dict()

class LabelViewer:
    def __init__(self, images, annotations):
        self.images = images
        self.num_images = len(images)
        self.anns = annotations
        self.fig, self.ax = plt.subplots()
        self.current = 0
        self.fig.canvas.mpl_connect('key_press_event', self.key_press_callback)
        self.redraw()
        plt.get_current_fig_manager().window.showMaximized()
        plt.show()

    def redraw(self):
        filename = os.path.basename(self.images._files[self.current])
        plt.cla()
        self.ax.imshow(self.images[self.current])
        self.ax.scatter(*zip(*self.anns[filename]), color='r', s=3)
        self.fig.suptitle(filename)
        self.fig.canvas.draw()

    def key_press_callback(self, event):
        if event.key == "right":
            self.current = min(self.current + 1, self.num_images - 1)
            self.redraw()
        elif event.key == "left":
            self.current = max(self.current - 1, 0)
            self.redraw()

parser = ArgumentParser()
parser.add_argument("image_dir")
parser.add_argument("annotations")
args = parser.parse_args()
image_dir = args.image_dir
images = imread_collection(image_dir + "/*.jpg", conserve_memory=False)
anns = load_annotations(args.annotations)

lv = LabelViewer(images, anns)
