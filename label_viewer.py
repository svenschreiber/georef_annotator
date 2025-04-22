import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
matplotlib.use("qtagg")

from PyQt6.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QVBoxLayout, QLabel, QComboBox, QPushButton, QFileDialog, QWidget, QToolButton, QLineEdit
from PyQt6.QtGui import QIntValidator
from PyQt6.QtCore import Qt 

from argparse import ArgumentParser
from skimage.io import imread_collection
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
        self.setWindowTitle("Change Label")
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

def sorted_items(d):
    return sorted(d.items(), key=lambda f: int(''.join(filter(str.isdigit, f[0]))))

class BulkLabelChangerDialog(QDialog):
    def __init__(self, labels, anns, num_images, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bulk Label Changer")
        self.setModal(True)
        self.labels_changed = False
        self.anns = anns
        layout = QVBoxLayout(self)
        row1 = QWidget()
        self.combo1 = QComboBox()
        self.combo1.addItems(labels)
        self.combo2 = QComboBox()
        self.combo2.addItems(labels)
        row1_layout = QHBoxLayout()
        row1_layout.addWidget(QLabel("Change label"))
        row1_layout.addWidget(self.combo1)
        row1_layout.addWidget(QLabel("to"))
        row1_layout.addWidget(self.combo2)
        row1.setLayout(row1_layout)
        layout.addWidget(row1)
        row2 = QWidget()
        self.lineedit1 = QLineEdit()
        self.lineedit1.setValidator(QIntValidator(1, num_images))
        self.lineedit2 = QLineEdit()
        self.lineedit2.setValidator(QIntValidator(1, num_images))
        row2_layout = QHBoxLayout()
        row2_layout.addWidget(QLabel("From frame"))
        row2_layout.addWidget(self.lineedit1)
        row2_layout.addWidget(QLabel("to"))
        row2_layout.addWidget(self.lineedit2)
        row2.setLayout(row2_layout)
        layout.addWidget(row2)
        row3 = QWidget()
        row3_layout = QHBoxLayout()
        change_btn = QPushButton()
        change_btn.clicked.connect(self.change_labels)
        change_btn.setText("Change")
        cancel_btn = QPushButton()
        cancel_btn.clicked.connect(self.accept)
        cancel_btn.setText("Cancel")
        row3_layout.addWidget(cancel_btn)
        row3_layout.addWidget(change_btn)
        row3.setLayout(row3_layout)
        layout.addWidget(row3)

    def change_labels(self):
        if self.lineedit1.hasAcceptableInput() and self.lineedit2.hasAcceptableInput():
            frame1, frame2 = int(self.lineedit1.text()), int(self.lineedit2.text())
            if frame1 > frame2: frame1, frame2 = frame2, frame1
            data = [points for i, (_, points) in enumerate(sorted_items(self.anns)) if i + 1 >= frame1 and i + 1 <= frame2]
            data = [p for ps in data for p in ps if p.label == self.combo1.currentText()]
            for p in data:
                p.label = self.combo2.currentText()
            self.labels_changed = True
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
    def __init__(self, canvas, parent, labels, anns_file, anns, img_size, num_images, redraw):
        super().__init__(canvas, parent)
        self.anns_file = anns_file
        self.anns = anns
        self.img_size = img_size

        self.remove_actions(["Home", "Back", "Forward", "Pan", "Zoom", "Subplots", "Customize"])

        self.addWidget(QLabel("Selected label"))
        self.combo = QComboBox()
        self.combo.addItems(labels)
        self.addWidget(self.combo)

        self.addSeparator()

        btn = QPushButton()
        btn.setText("Bulk Label Changer")
        def open_bulk_label_changer():
            dialog = BulkLabelChangerDialog(labels, anns, num_images, self)
            dialog.exec()
            if dialog.labels_changed: redraw()

        btn.clicked.connect(open_bulk_label_changer)
        self.addWidget(btn)

    def remove_actions(self, actions):
        for action in self.actions():
            if action.text() in actions or action.isSeparator():
                self.removeAction(action)

    def save_figure(self, *args, **kwargs):
        file_path, _ = QFileDialog.getSaveFileName(None, "Save Labels", self.anns_file,"CSV (*.csv);;All Files (*)")
        if file_path:
            with open(file_path, "w") as f:
                for img_file, points in sorted_items(self.anns):
                    for p in points:
                        f.write(f"{p.label},{p.coords[0]},{p.coords[1]},{img_file},{self.img_size[0]},{self.img_size[1]}\n")

class LabelViewer:
    def __init__(self, args):
        image_dir = args.image_dir
        file_list = [os.path.join(args.image_dir, file) for file in os.listdir(args.image_dir) if file.endswith('.jpg')]
        file_list.sort(key=lambda f: int(''.join(filter(str.isdigit, f))))
        self.images = imread_collection(file_list, conserve_memory=False)
        img_height, img_width, _ = self.images[0].shape
        self.anns = load_annotations(args.annotations)
        self.label_names = load_labels(args.label_names_file)
        self.num_images = len(self.images)
        self.fig, self.ax = plt.subplots()
        self.current = 0
        self.selected_point = None
        self.fig.canvas.mpl_connect('key_press_event', self.key_press_callback)
        self.fig.canvas.mpl_connect('pick_event', self.pick_callback)
        self.fig.canvas.mpl_connect('button_press_event', self.button_press_callback)
        self.fig.canvas.mpl_connect('button_release_event', self.button_release_callback)
        self.fig.canvas.mpl_connect('motion_notify_event', self.motion_notify_callback)
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
                break

        central = QWidget()
        layout = QVBoxLayout()
        self.toolbar = CustomToolbar(canvas, window, self.label_names, args.annotations, self.anns, (img_width, img_height), self.num_images, self.redraw)
        layout.addWidget(self.toolbar)
        layout.addWidget(canvas)
        central.setLayout(layout)
        window.setCentralWidget(central)

        plt.show()

    def redraw(self):
        filename = self.get_current_filename()
        plt.cla()
        self.ax.imshow(self.images[self.current])
        coords, labels = self.get_point_list()
        cmap = matplotlib.colormaps['tab10']
        label_to_color = {label: cmap(i % cmap.N) for i, label in enumerate(self.label_names)}
        color_values = [label_to_color[label] for label in labels]
        if len(coords) > 0: self.sc = self.ax.scatter(*zip(*coords), c=color_values, picker=True)
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

    def button_release_callback(self, event):
        self.selected_point = None

    def pick_callback(self, event):
        coords = self.sc.get_offsets()[event.ind[0]]
        p = self.get_point_by_coords(coords)
        if event.mouseevent.button == 1:
            self.selected_point = p
        if event.mouseevent.button == 3:
            dialog = PointDialog(self.label_names, p, event.canvas.manager.window)
            dialog.exec()
            p.label = dialog.combo.currentText()
            if dialog.should_delete: self.get_current_anns().remove(p)
            self.redraw()

    def motion_notify_callback(self, event):
        if self.selected_point is None or event.inaxes != self.ax: return
        self.selected_point.coords = (int(event.xdata), int(event.ydata))
        self.redraw()

    def button_press_callback(self, event):
        if event.xdata is None or event.ydata is None: return
        if event.button == 1 and self.selected_point is None:
            x, y = int(event.xdata), int(event.ydata)
            label = self.toolbar.combo.currentText()
            self.get_current_anns().append(Point(x, y, label))
            self.redraw()

parser = ArgumentParser()
parser.add_argument("image_dir")
parser.add_argument("annotations")
parser.add_argument("label_names_file")
args = parser.parse_args()

lv = LabelViewer(args)
