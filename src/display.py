import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import asyncio

class Display:
    def __init__(self, variables):
        self.variables = variables
        self.fig, self.ax = plt.subplots()
        self.bars = self.ax.bar(self.variables.keys(), self.variables.values(), color='blue')
        self.ax.set_ylim(0, max(self.variables.values()) * 1.2)  # Set y-axis limit slightly above max value
        self.ax.set_title("Live Input Values")
        self.ax.set_ylabel("Value")

    def update_bars(self, _):
        """Update the heights of the bars based on the current variable values."""
        for bar, value in zip(self.bars, self.variables.values()):
            bar.set_height(value)

    async def start_async(self):
        """Asynchronous plotting."""
        ani = FuncAnimation(self.fig, self.update_bars, interval=100, cache_frame_data=False)

        # Keep the event loop running while the plot is open
        while plt.fignum_exists(self.fig.number):
            plt.pause(0.1)  # Allow matplotlib to update the plot
            await asyncio.sleep(0.1)  # Yield control to the asyncio event loop