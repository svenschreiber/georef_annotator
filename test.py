import matplotlib.pyplot as plt
import numpy as np

# Sample data
x = np.random.rand(10)
y = np.random.rand(10)

fig, ax = plt.subplots()
sc = ax.scatter(x, y, s=100, picker=True)  # Enable picking

selected_index = None  # Keep track of which point is selected

def on_pick(event):
    global selected_index
    # Find the index of the picked point
    selected_index = event.ind[0]

def on_press(event):
    # Optional: You could start drag on press here
    pass

def on_release(event):
    global selected_index
    selected_index = None  # Deselect when mouse is released

def on_motion(event):
    global selected_index
    if selected_index is None or event.inaxes != ax:
        return

    # Update the data
    x[selected_index] = event.xdata
    y[selected_index] = event.ydata
    sc.set_offsets(np.c_[x, y])
    fig.canvas.draw_idle()

# Connect events
fig.canvas.mpl_connect('pick_event', on_pick)
fig.canvas.mpl_connect('button_press_event', on_press)
fig.canvas.mpl_connect('button_release_event', on_release)
fig.canvas.mpl_connect('motion_notify_event', on_motion)

plt.show()
