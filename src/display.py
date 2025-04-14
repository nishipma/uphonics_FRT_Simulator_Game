from matplotlib.animation import FuncAnimation
from collections import deque
import asyncio
import matplotlib.pyplot as plt
import numpy as np

class Display:
    def __init__(self, variables,control_variables):
        self.variables = variables
        self.control_variables = control_variables
        self.fig, (self.ax, self.ax_pg_vs_detuning) = plt.subplots(2,1, figsize=(8,6))
        self.fig.canvas.mpl_connect('close_event', self.on_close)
        self.ax2 = self.ax.twinx()
        self.bars = None
        self.qe_bar = None

        self._initialize_primary_variables()
        self._initialize_primary_bars()
        self._initialize_Qe_bar()

         # Initialize the Pg vs detuning plot
        self.ax_pg_vs_detuning.set_title("Pg vs Detuning")
        self.ax_pg_vs_detuning.set_xlabel("Detuning")
        self.ax_pg_vs_detuning.set_ylabel("Pg")
        self.pg_vs_detuning_scatter = self.ax_pg_vs_detuning.scatter([], [], c=[], marker='.',label="Pg vs Detuning")
        #self.pg_vs_detuning_line, = self.ax_pg_vs_detuning.plot([], [], 'r.', label="Pg vs Detuning")
        self.ax_pg_vs_detuning.legend()

        # Data for Pg vs detuning
        maxlen = 1130
        self.detuning_data = deque(maxlen=maxlen)
        self.pg_colours = deque(maxlen=maxlen)
        self.pg_data = deque(maxlen=maxlen)

    # @property
    # def plotting_colour(self):
    #     """PLotting Colour"""
    #     return self.control_variables['Plotting_Colour']

    def on_close(self, event):
        """Handle the close event of the figure."""
        plt.close(self.fig)
        tasks = asyncio.all_tasks(asyncio.get_event_loop())
        for task in tasks:
            task.cancel()
        # Wait for all tasks to finish
        async def shutdown():
            await asyncio.gather(*tasks, return_exceptions=True)

        asyncio.create_task(shutdown())  # Schedule the shutdown coroutine

    def _initialize_primary_variables(self):
        """Extract and organize primary variable names and values."""
        self.variable_names = ['FRT On'] + [
            name for name in self.variables.keys() if name not in ['Qe', 'FRT On']
        ]
        self.variable_values = [self.variables['FRT On']['value']] + [
            var['value'] for name, var in self.variables.items() if name not in ['Qe', 'FRT On']
        ]

    def _initialize_primary_bars(self):
        """Set up the primary variable bars."""
        self.bars = self.ax.bar(self.variable_names, self.variable_values, color='blue')
        self.ax.set_ylim(0, self._calculate_primary_y_axis_limit())
        self.ax.set_title("Live Input Values")
        self.ax.set_ylabel("Value")
        self.ax.set_xticks(range(len(self.variable_names)))
        self.ax.set_xticklabels(self.variable_names)

    def _calculate_primary_y_axis_limit(self):
        """Calculate the y-axis limit for the primary variables."""
        return max(
            var['range'][1] if 'range' in var else 1  # Default to 1 if 'range' is missing
            for name, var in self.variables.items()
            if name != 'Qe'
        ) * 1.2

    def _initialize_Qe_bar(self):
        """Set up the secondary bar chart for Qe, if it exists."""
        if 'Qe' in self.variables:
            qe_value = self.variables['Qe']['value']
            self.qe_bar = self.ax2.bar(
                [len(self.variable_names)],  # Position Qe after the primary bars
                [qe_value],
                color='red',
                label='Qe'
            )
            self.ax2.set_ylim(0, self._calculate_secondary_y_axis_limit())
            self.ax2.set_ylabel("Qe Value")
            self._update_x_axis_labels()

    def _calculate_secondary_y_axis_limit(self):
        """Calculate the y-axis limit for the secondary variable Qe."""
        qe_range = self.variables['Qe'].get('range', [0, 1])  # Default range [0, 1] if missing
        return qe_range[1] * 1.2

    def _update_x_axis_labels(self):
        """Update x-axis labels to include Qe."""
        self.ax.set_xticks(range(len(self.variable_names) + 1))
        self.ax.set_xticklabels(self.variable_names + ['Qe'])

    def update_bars(self, _):
        """Update the heights of the bars based on the current variable values."""
        for bar, name in zip(self.bars, self.variable_names):
            # Update the bar height with the current value of the variable
            bar.set_height(self.variables[name]['value'])

        # Update the Qe bar if it exists
        if self.qe_bar:
            qe_value = self.variables['Qe']['value']
            self.qe_bar[0].set_height(qe_value)


    async def start_async(self, queue):
        """Asynchronous plotting without blitting."""
        def update(_):
            """Update the plot."""
            self.update_bars(_)
            if len(self.detuning_data) > 0 and len(self.pg_data) > 0:
                # Update the line data with the latest detuning and Pg values
                self.pg_vs_detuning_scatter.set_offsets(np.column_stack((self.detuning_data, self.pg_data)))
                self.pg_vs_detuning_scatter.set_color(self.pg_colours)
                # Manually update the axes limits
                self.ax_pg_vs_detuning.set_xlim(min(self.detuning_data), max(self.detuning_data))
                self.ax_pg_vs_detuning.set_ylim(min(self.pg_data), max(self.pg_data))
                # self.ax_pg_vs_detuning.relim()  # Recalculate limits
                # self.ax_pg_vs_detuning.autoscale_view()  # Autoscale the view
                
        # Use FuncAnimation without blitting
        ani = FuncAnimation(
            self.fig,
            update,
            interval=10,  # Update interval in milliseconds
            cache_frame_data=False,
        )

        batch_size = 10  # Number of points to plot at once

        while True:
                            
            batch = []
            # Get the latest values from the queue
            for _ in range(batch_size):
                data = await queue.get()
                batch.append(data)

            #Process the batch
            for data in batch:
                detuning = data["Detuning"]
                colour = self.control_variables['Plotting_Colour']
                pg = data["Pg"]

                # Append the new data to the circular buffers
                self.pg_colours.append(colour)
                self.detuning_data.append(detuning)
                self.pg_data.append(pg)

            # Allow matplotlib to update the plot
            plt.pause(0.001)
            await asyncio.sleep(0)
            #plt.show()

###
    # def __init__(self, variables):
    #     self.variables = variables
    #     self.time = 0
    #     self.detuning = 0
    #     self.Pg = 0

    #     # Create a figure for Pg vs detuning
    #     self.fig, (self.ax_bars, self.ax_pg_vs_detuning) = plt.subplots(2, 1, figsize=(8, 6))

    #     # Initialize the bar chart for primary variables
    #     self.bars = self.ax_bars.bar(self.variables.keys(), [var['value'] for var in self.variables.values()], color='blue')
    #     self.ax_bars.set_title("Live Input Values")
    #     self.ax_bars.set_ylabel("Value")

    #     # Initialize the Pg vs detuning plot
    #     self.ax_pg_vs_detuning.set_title("Pg vs Detuning")
    #     self.ax_pg_vs_detuning.set_xlabel("Detuning")
    #     self.ax_pg_vs_detuning.set_ylabel("Pg")
    #     self.pg_vs_detuning_line, = self.ax_pg_vs_detuning.plot([], [], 'r-', label="Pg vs Detuning")
    #     self.ax_pg_vs_detuning.legend()

    #     # Data for Pg vs detuning
    #     self.detuning_data = []
    #     self.pg_data = []

    # def update_bars(self, _):
    #     """Update the heights of the bars based on the current variable values."""
    #     for bar, (name, var) in zip(self.bars, self.variables.items()):
    #         bar.set_height(var['value'])

    # def update_pg_vs_detuning(self):
    #     """Update the Pg vs detuning plot."""
    #     self.pg_vs_detuning_line.set_data(self.detuning_data, self.pg_data)
    #     self.ax_pg_vs_detuning.relim()  # Recalculate limits
    #     self.ax_pg_vs_detuning.autoscale_view()  # Autoscale the view

    # async def start_async(self, queue):
    #     """Asynchronous plotting."""
    #     ani = FuncAnimation(self.fig, self.update_bars, interval=100, cache_frame_data=False)

    #     # Continuously consume values from the queue
    #     while True:
    #         # Get the latest values from the queue
    #         data = await queue.get()
    #         self.detuning = data["Detuning"]
    #         self.Pg = data["Pg"]

    #         # Append the new data to the Pg vs detuning plot
    #         self.detuning_data.append(self.detuning)
    #         self.pg_data.append(self.Pg)

    #         # Update the Pg vs detuning plot
    #         self.update_pg_vs_detuning()

    #         # Allow matplotlib to update the plot
    #         plt.pause(0.02)
    #         await asyncio.sleep(0.02)  # Yield control to the asyncio event loop