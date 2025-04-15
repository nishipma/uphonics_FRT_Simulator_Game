from matplotlib.animation import FuncAnimation
from collections import deque
import asyncio
import matplotlib.pyplot as plt
import numpy as np

class Display:
    def __init__(self, input_variables,calculated_variables):
        self.input_variables = input_variables
        self.calculated_variables = calculated_variables
        self.fig, (self.ax, self.ax_pg_vs_detuning) = plt.subplots(2,1, figsize=(8,6))
        self.fig.canvas.mpl_connect('close_event', self.on_close)
        self.ax2 = self.ax.twinx()
        self.ax2.set_yscale('log')
        self.ax2.set_ylim(self.input_variables['Qe']['range'])
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
        self.ax_pg_vs_detuning.legend()

        # Data for Pg vs detuning
        maxlen = 1130
        self.pg_colours = deque(maxlen=maxlen)
        self.detuning_data = deque(maxlen=maxlen)
        self.pg_data = deque(maxlen=maxlen)
        self.detuning_FRT_data = deque(maxlen=maxlen)
        self.pg_FRT_data = deque(maxlen=maxlen)


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
            name for name in self.input_variables.keys() if name not in ['Qe', 'FRT On']
        ]
        self.variable_values = [self.input_variables['FRT On']['value']] + [
            var['value'] for name, var in self.input_variables.items() if name not in ['Qe', 'FRT On']
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
            for name, var in self.input_variables.items()
            if name != 'Qe'
        ) * 1.2

    def _initialize_Qe_bar(self):
        """Set up the secondary bar chart for Qe, if it exists."""
        if 'Qe' in self.input_variables:
            qe_value = self.input_variables['Qe']['value']
            self.qe_bar = self.ax2.bar(
                [len(self.variable_names)],  # Position Qe after the primary bars
                [qe_value],
                color='red',
                label='Qe'
            )
            self.ax2.set_ylabel("Qe Value")

            # Add a horizontal line for Qe_opt
            # Get the width of the Qe bar
            bar_width = self.qe_bar[0].get_width()
            # Calculate the x-coordinates for the dashed line
            qe_bar_x = len(self.variable_names)  # X-position of the Qe bar
            x_start = qe_bar_x - bar_width / 2
            x_end = qe_bar_x + bar_width / 2

            # Add a horizontal dashed line limited to the Qe bar
            qe_opt_value = 10**9  # Replace with the actual Qe_opt value
            self.qe_opt_line, = self.ax2.plot(
                [x_start, x_end], [qe_opt_value, qe_opt_value],
                color='blue', linestyle='--', label='Qe_opt'
            )

            self._update_x_axis_labels()

    def _update_x_axis_labels(self):
        """Update x-axis labels to include Qe."""
        self.ax.set_xticks(range(len(self.variable_names) + 1))
        self.ax.set_xticklabels(self.variable_names + ['Qe'])

    def update_bars(self, _):
        """Update the heights of the bars based on the current variable values."""
        for bar, name in zip(self.bars, self.variable_names):
            # Update the bar height with the current value of the variable
            bar.set_height(self.input_variables[name]['value'])

        # Update the Qe bar if it exists
        if self.qe_bar:
            qe_value = self.input_variables['Qe']['value']
            self.qe_bar[0].set_height(qe_value)

        # # Update the Qe_opt line dynamically
        # if hasattr(self, 'qe_opt_line'):
        #     qe_opt_value = self.variables['Qe_opt']['value']
        #     bar_width = self.qe_bar[0].get_width()
        #     qe_bar_x = len(self.variable_names)  # X-position of the Qe bar
        #     x_start = qe_bar_x - bar_width / 2
        #     x_end = qe_bar_x + bar_width / 2
        #     self.qe_opt_line.set_data([x_start, x_end], [qe_opt_value, qe_opt_value])


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
                # Update limits only if necessary
                largest_detuning = max(np.abs(min(self.detuning_data)),max(self.detuning_data))
                x_scale = self.ax_pg_vs_detuning.get_xlim()[1]
                if  largest_detuning > x_scale or largest_detuning<0.8*x_scale:
                    self.ax_pg_vs_detuning.set_xlim(-1.05*largest_detuning, 1.05*largest_detuning)
                largest_power = max(self.pg_data)
                largest_yscale = self.ax_pg_vs_detuning.get_ylim()[1]
                if largest_power > largest_yscale or largest_power<0.8*largest_yscale:
                    self.ax_pg_vs_detuning.set_ylim(0, 1.05*largest_power)
                
                
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
                colour = self.calculated_variables['Plotting_Colour']
                pg = data["Pg"]
                detuning_FRT = data["Detuning FRT"]
                pg_FRT = data["Pg FRT"]

                # Append the new data to the circular buffers
                self.pg_colours.append(colour)
                self.detuning_data.append(detuning)
                self.pg_data.append(pg)
                self.detuning_FRT_data.append(detuning_FRT)
                self.pg_FRT_data.append(pg_FRT)

            # Allow matplotlib to update the plot
            plt.pause(0.001)
            await asyncio.sleep(0)

