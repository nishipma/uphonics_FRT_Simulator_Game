import matplotlib
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
matplotlib.rcParams['keymap.save'] = [] # Disable key press saving, unbinds s key
matplotlib.rcParams['keymap.fullscreen'] = [] # Disable key press fullscreen, unbinds f key

class Display:
    def __init__(self, variables):
        self.variables = variables
        self.fig, self.ax = plt.subplots()
        self.bars = self.ax.bar(self.variables.keys(), self.variables.values(), color='blue')
        self.ax.set_ylim(0, max(self.variables.values()) * 1.2)  # Set y-axis limit slightly above max value
        self.ax.set_title("Live Input Values")
        self.ax.set_ylabel("Value")

    def update_bars(self):
        """Update the heights of the bars based on the current variable values."""
        for bar, value in zip(self.bars, self.variables.values()):
            bar.set_height(value)

    def animate(self, i):
        """Animation function to redraw the plot."""
        self.update_bars()

    def start(self):
        """Start the live plot."""
        ani = FuncAnimation(self.fig, self.animate, interval=100)
        plt.show()