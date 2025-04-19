import matplotlib.pyplot as plt
from argparse import ArgumentParser
from skimage.io import imread_collection
import matplotlib
matplotlib.use("qtagg")
from PyQt6.QtWidgets import QDialog, QFormLayout, QLabel, QComboBox, QPushButton, QFileDialog
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
import os
import pandas as pd

class Point:
    def __init__(self, x, y, label):
        self.coords, self.label = (x, y), label

    def has_coords(self, x, y):
        return self.coords[0] == int(x) and self.coords[1] == int(y)

class PointDialog(QDialog):
    def __init__(self, labels, point, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Test")
        self.setModal(True)
        layout = QFormLayout(self)
        self.combo = QComboBox()
        self.combo.addItems(labels)
        self.combo.setCurrentText(point.label)
        layout.addRow(QLabel("Label:"), self.combo)
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self.set_delete)
        self.should_delete = False
        button = QPushButton("Done")
        button.clicked.connect(self.accept)
        button.setDefault(True)
        layout.addRow(delete_btn, button)

    def set_delete(self):
        self.should_delete = True
        self.accept()

def load_labels(file):
    with open(file, "r") as f: return [line.strip() for line in f]

def load_annotations(file):
    df = pd.read_csv(file, sep=",", header=None)
    df.columns = ['label', 'x', 'y', 'filename', 'width', 'height']
    grouped = df.groupby('filename').apply(
        lambda g: [Point(row['x'], row['y'], str(row['label'])) for _, row in g.iterrows()],
        include_groups=False
    )
    return grouped.to_dict()

class CustomToolbar(NavigationToolbar2QT):
    def __init__(self, canvas, parent, anns_file, anns, img_size):
        super().__init__(canvas, parent)
        self.anns_file = anns_file
        self.anns = anns
        self.img_size = img_size

    def save_figure(self, *args, **kwargs):
        # Custom behavior: show a message box and skip default save dialog
        file_path, _ = QFileDialog.getSaveFileName(None, "Save Labels", self.anns_file,"CSV (*.csv);;All Files (*)")
        if file_path:
            with open(file_path, "w") as f:
                for img_file, points in self.anns.items():
                    for p in points:
                        f.write(f"{p.label},{p.coords[0]},{p.coords[1]},{img_file},{self.img_size[0]},{self.img_size[1]}\n")

class LabelViewer:
    def __init__(self, args):
        image_dir = args.image_dir
        self.images = imread_collection(image_dir + "/*.jpg", conserve_memory=False)
        img_height, img_width, _ = self.images[0].shape
        self.anns = load_annotations(args.annotations)
        self.label_names = load_labels(args.label_names_file)
        self.num_images = len(self.images)
        self.fig, self.ax = plt.subplots()
        self.current = 0
        self.fig.canvas.mpl_connect('key_press_event', self.key_press_callback)
        self.fig.canvas.mpl_connect('pick_event', self.pick_callback)
        self.sc = None
        self.redraw()
        window = plt.get_current_fig_manager().window
        canvas = plt.get_current_fig_manager().canvas
        window.showMaximized()
        layout = window.layout()
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            if isinstance(widget, NavigationToolbar2QT):
                layout.removeWidget(widget)
                widget.setParent(None)

        custom_toolbar = CustomToolbar(canvas, window, args.annotations, self.anns, (img_width, img_height))
        layout.addWidget(custom_toolbar)
        plt.show()

    def redraw(self):
        filename = self.get_current_filename()
        plt.cla()
        self.ax.imshow(self.images[self.current])
        coords, labels = self.get_point_list()
        cmap = matplotlib.colormaps['tab10']
        label_to_color = {label: cmap(i % cmap.N) for i, label in enumerate(self.label_names)}
        color_values = [label_to_color[label] for label in labels]

        self.sc = self.ax.scatter(*zip(*coords), c=color_values, picker=True)
        self.fig.suptitle(f"{filename} ({self.current + 1}/{self.num_images})")
        self.fig.canvas.draw()

    def key_press_callback(self, event):
        if event.key == "right":
            self.current = min(self.current + 1, self.num_images - 1)
            self.redraw()
        elif event.key == "left":
            self.current = max(self.current - 1, 0)
            self.redraw()

    def get_current_filename(self):
        return os.path.basename(self.images._files[self.current])

    def get_current_anns(self):
        return self.anns[self.get_current_filename()]

    def get_point_list(self):
        coords = [p.coords for p in self.get_current_anns()]
        labels = [p.label for p in self.get_current_anns()]
        return coords, labels

    def get_point_by_coords(self, coords):
        points = [p for p in self.get_current_anns() if p.has_coords(*coords)]
        return points[0] if len(points) > 0 else None

    def pick_callback(self, event):
        coords = self.sc.get_offsets()[event.ind[0]]
        p = self.get_point_by_coords(coords)
        print(p.__dict__)
        dialog = PointDialog(self.label_names, p, event.canvas.manager.window)
        dialog.exec()
        p.label = dialog.combo.currentText()
        if dialog.should_delete: self.get_current_anns().remove(p)
        self.redraw()

parser = ArgumentParser()
parser.add_argument("image_dir")
parser.add_argument("annotations")
parser.add_argument("label_names_file")
args = parser.parse_args()

lv = LabelViewer(args)
