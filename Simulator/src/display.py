from matplotlib.animation import FuncAnimation
from collections import deque
import asyncio
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np

class Display:
    def __init__(self, input_variables,calculated_variables, event_system):
        self.input_variables = input_variables
        self.calculated_variables = calculated_variables
        self.calculated_variable_queue = event_system.add_listener("calculated variables changed")
        self.input_variable_queue = event_system.add_listener("input variables changed")

        #Cache for calculated variables
        self._cached_calculated_variables = {}
        self._calculated_cache_valid =False

        #Cache for input variables
        self._cached_input_variables = {}
        self._input_cache_valid =False

        
        self.fig, self.axs = plt.subplots(2,2)
        #Assign axes
        self.ax_schem = self.axs[0,0]
        self.ax_bars = self.axs[0,1]
        self.ax_pg_vs_time = self.axs[1,0]
        self.ax_pg_vs_detuning = self.axs[1,1]

        self.fig.canvas.mpl_connect('close_event', self.on_close)
        self.ax_bars2 = self.ax_bars.twinx()
        self.ax_bars2.set_yscale('log')
        self.ax_bars2.set_ylim(self.input_variables['Qe']['range'])
        self.bars = None
        self.qe_bar = None

        self._initialize_primary_variables()
        self._initialize_primary_bars()
        self._initialize_Qe_bar()

        # Display a PNG in ax_schem
        self._display_schem_image()

         # Initialize the Pg vs detuning plot
        self.ax_pg_vs_detuning.set_title("Power required vs Detuning")
        self.ax_pg_vs_detuning.set_xlabel("Detuning [Hz]")
        self.ax_pg_vs_detuning.set_ylabel("RF Power [W]")
        self.pg_vs_detuning_scatter = self.ax_pg_vs_detuning.scatter([], [], c=[], marker='.',label="Pg vs Detuning")
        self.pg_vs_detuning_scatter_FRT = self.ax_pg_vs_detuning.scatter([], [], c=[], marker='.')
        self.pg_vs_detuning_avg_line = self.ax_pg_vs_detuning.plot([], [], c='black', linestyle='-', label="Avg Pg vs Detuning")[0]
        self.pg_vs_detuning_avg_line_FRT = self.ax_pg_vs_detuning.plot([], [], c='black', linestyle='-')[0]
        self.ax_pg_vs_detuning.legend()

        # Initialize the Pg vs time plot
        self.ax_pg_vs_time.set_title("Power required vs Time")
        self.ax_pg_vs_time.set_xlabel("Time [ms]")
        self.ax_pg_vs_time.set_ylabel("RF Power [W]")
        self.pg_vs_time_scatter = self.ax_pg_vs_time.scatter([], [], c=[], marker='.',label="Pg vs Time")
        self.pg_vs_time_scatter_FRT = self.ax_pg_vs_time.scatter([], [], c=[], marker='.')
        self.pg_vs_time_avg_line = self.ax_pg_vs_time.plot([], [], c='black', linestyle='-', label="Avg Pg vs Time")[0]
        self.ax_pg_vs_time.legend()

        # Data for Pg vs detuning
        maxlen = 1130
        self.pg_colours = deque(maxlen=maxlen)
        self.detuning_data = deque(maxlen=maxlen)
        self.pg_data = deque(maxlen=maxlen)
        self.detuning_FRT_data = deque(maxlen=maxlen)
        self.pg_FRT_data = deque(maxlen=maxlen)
        self.pg_avg_data = deque(maxlen=maxlen)
        self.pg_FRT_avg_data = deque(maxlen=maxlen)
        
        # Additional Data for Pg vs time
        self.time_data = deque(maxlen=maxlen)


    @property
    def Plotting_Colour(self):
        """Dynamically retrieve the value of Plotting_Colour from calculated variables."""
        return self._get_cached_calculated_variables('Plotting_Colour')
    
    @property
    def Qe_opt(self):
        """Dynamically retrieve the value of Qe_opt from calculated variables."""
        return self._get_cached_calculated_variables('Qe_opt')
    
    @property
    def Qe_opt_FRT(self):
        """Dynamically retrieve the value of Qe_opt_FRT from calculated variables."""
        return self._get_cached_calculated_variables('Qe_opt_FRT')
    
    @property
    def Qe(self):
        """Dynamically retrieve the value of Qe from input variables."""
        return self._get_cached_input_variables('Qe')
    
    @property
    def FoM(self):
        """Dynamically retrieve the value of FoM from input variables."""
        return self._get_cached_input_variables('FoM')
    
    @property
    def tuning_range(self):
        """Dynamically retrieve the value of tuning_range from input variables."""
        return self._get_cached_input_variables('tuning_range')
    
    @property
    def uphonics_range(self):
        """Dynamically retrieve the value of uphonics_range from input variables."""
        return self._get_cached_input_variables('uphonics_range')
    
    @property
    def FRT_On(self):
        """Dynamically retrieve the value of FRT_On from input variables."""
        return self._get_cached_input_variables('FRT_On')

    def _display_schem_image(self):
        """Display a PNG image in the ax_schem subplot."""
        # Load the image from the assets/images folder
        img = mpimg.imread('../assets/images/Schematic_Controls_Instructions.png') 
        # Display the image in the ax_schem subplot
        self.ax_schem.imshow(img)
        # Remove axes (optional)
        self.ax_schem.axis('off')
    
    async def _listen_for_input_changes(self):
        """Listen for changes in input variables and invalidate the cache."""
        while True:
            # Wait for a change in input variables
            await self.input_variable_queue.get()
            # Invalidate the cache when a change is detected
            self._invalidate_input_cache()

    def _invalidate_input_cache(self):
        """Invalidate the cache when input variables change."""
        self._input_cache_valid = False

    def _get_cached_input_variables(self, key):
        """Retrieve a cached value or recalculate it if the cache is invalid."""
        if not self._input_cache_valid:
            # Recalculate the value and update the cache
            self._recalculate_input_variables()
        return self._cached_input_variables[key]
    
    def _recalculate_input_variables(self):
        """Recalculate all input variables and update the cache."""
        for key in self.input_variables:
            # Recalculate the input variable
            value = self.input_variables[key]['value']
            self._cached_input_variables[key] = value

    async def _listen_for_calculated_changes(self):
        """Listen for changes in calculated variables and invalidate the cache."""
        while True:
            # Wait for a change in calculated variables
            await self.calculated_variable_queue.get()
            # Invalidate the cache when a change is detected
            self._invalidate_calculated_cache()

    def _invalidate_calculated_cache(self):
        """Invalidate the cache when calculated variables change."""
        self._calculated_cache_valid = False

    def _get_cached_calculated_variables(self, key):
        """Retrieve a cached value or recalculate it if the cache is invalid."""
        if not self._calculated_cache_valid:
            # Recalculate the value and update the cache
            self._recalculate_calculated_variables()
        return self._cached_calculated_variables[key]
    
    def _recalculate_calculated_variables(self):
        """Recalculate all calculated variables and update the cache."""
        for key in self.calculated_variables:
            # Recalculate the calculated variable
            value = self.calculated_variables[key]
            self._cached_calculated_variables[key] = value

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
        self.variable_names = ['FRT_On'] + [
            name for name in self.input_variables.keys() if name not in ['Qe', 'FRT_On']
        ]
        self.variable_values = [self.input_variables['FRT_On']['value']] + [
            var['value'] for name, var in self.input_variables.items() if name not in ['Qe', 'FRT_On']
        ]

    def _initialize_primary_bars(self):
        """Set up the primary variable bars."""
        self.bars = self.ax_bars.bar(self.variable_names, self.variable_values, color='blue')
        self.ax_bars.set_ylim(0, self._calculate_primary_y_axis_limit())
        self.ax_bars.set_title("Live Input Values")
        self.ax_bars.set_ylabel("Value")
        self.ax_bars.set_xticks(range(len(self.variable_names)))
        self.ax_bars.set_xticklabels(self.variable_names)

    def _calculate_primary_y_axis_limit(self):
        """Calculate the y-axis limit for the primary variables."""
        return max(self.FoM,self.uphonics_range,self.tuning_range) * 1.2

    def _initialize_Qe_bar(self):
        """Set up the secondary bar chart for Qe"""
        
        self.qe_bar = self.ax_bars2.bar(
            [len(self.variable_names)],  # Position Qe after the primary bars
            [self.Qe],
            color='red',
            label='Qe'
        )
        self.ax_bars2.set_ylabel("Qe Value")

        # Add a horizontal line for Qe_opt
        # Get the width of the Qe bar
        bar_width = self.qe_bar[0].get_width()
        # Calculate the x-coordinates for the dashed line
        qe_bar_x = len(self.variable_names)  # X-position of the Qe bar
        x_start = qe_bar_x - bar_width / 2
        x_end = qe_bar_x + bar_width / 2

        # Add a horizontal dashed line limited to the Qe bar
        qe_opt_value = self.Qe_opt  # Use the value from the calculated variables
        self.qe_opt_line, = self.ax_bars2.plot(
            [x_start, x_end], [qe_opt_value, qe_opt_value],
            color='blue', linestyle='--', label='Qe_opt'
        )

        self._update_x_axis_labels()

    def _update_x_axis_labels(self):
        """Update x-axis labels to include Qe."""
        self.ax_bars.set_xticks(range(len(self.variable_names) + 1))
        self.ax_bars.set_xticklabels(self.variable_names + ['Qe'])

    def update_bars(self, _):
        """Update the heights of the bars based on the current variable values."""
        for bar, name in zip(self.bars, self.variable_names):
            # Use the property to get the current value of the variable
            if hasattr(self, name):  # Check if the property exists
                bar.set_height(getattr(self, name))
                self.ax_bars.set_ylim(0, self._calculate_primary_y_axis_limit())
            else:
                raise AttributeError(f"Property '{name}' does not exist in the display class.")

        # Update the Qe bar
        self.qe_bar[0].set_height(self.Qe)
        # Update the y-value of the Qe_opt line
        if self.FRT_On:
            qe_opt_value = self.Qe_opt_FRT  # Get the updated value of Qe_opt_FRT
        else:
            qe_opt_value = self.Qe_opt  # Get the updated value of Qe_opt
        self.qe_opt_line.set_ydata([qe_opt_value, qe_opt_value])  # Update the y-data

        
    async def start_async(self, queue):
        """Asynchronous plotting"""
        def update(_):
            """Update the plot."""
            #Update bar chart
            self.update_bars(_)

            #Update Pg vs detuning plot
            if len(self.detuning_data) > 0 and len(self.pg_data) > 0:
                # Update the Pg vs detuning data with the latest detuning and Pg values
                self.pg_vs_detuning_scatter.set_offsets(np.column_stack((self.detuning_data, self.pg_data)))
                self.pg_vs_detuning_scatter_FRT.set_offsets(np.column_stack((self.detuning_FRT_data, self.pg_FRT_data)))
                self.pg_vs_detuning_avg_line.set_data([min(self.detuning_data),max(self.detuning_data)], [self.pg_avg_data[-1],self.pg_avg_data[-1]])
                if self.FRT_On:
                    #For FRT Off Data set colour to light grey and transparency to 0.5
                    #For FRT On Data set coloour to pg_colours and transparency to 1.0
                    self.pg_vs_detuning_scatter.set_alpha(0.5)
                    self.pg_vs_detuning_scatter.set_color('lightgrey')
                    self.pg_vs_detuning_avg_line.set_alpha(0.5)
                    self.pg_vs_detuning_avg_line.set_color('lightgrey')
                    self.pg_vs_detuning_scatter_FRT.set_alpha(1.0)
                    self.pg_vs_detuning_scatter_FRT.set_color(self.pg_colours)
                else:
                    #For FRT Off Data set the colour to pg_colours and transparency to 1.0
                    #For FRT On Data set colour to light grey and transparency to 0.5
                    self.pg_vs_detuning_scatter.set_alpha(1.0)
                    self.pg_vs_detuning_scatter.set_color(self.pg_colours)
                    self.pg_vs_detuning_avg_line.set_alpha(1.0)
                    self.pg_vs_detuning_avg_line.set_color(self.pg_colours[-1])
                    self.pg_vs_detuning_scatter_FRT.set_alpha(0.5)
                    self.pg_vs_detuning_scatter_FRT.set_color('lightgrey')
                
                
                
                # Update limits only if necessary
                largest_detuning = max(np.abs(min(self.detuning_data)),max(self.detuning_data))
                x_scale = self.ax_pg_vs_detuning.get_xlim()[1]
                if  largest_detuning > x_scale or largest_detuning<0.8*x_scale:
                    self.ax_pg_vs_detuning.set_xlim(-1.05*largest_detuning, 1.05*largest_detuning)
                largest_power = max(self.pg_data)
                largest_yscale = self.ax_pg_vs_detuning.get_ylim()[1]
                if largest_power > largest_yscale or largest_power<0.8*largest_yscale:
                    self.ax_pg_vs_detuning.set_ylim(0, 1.05*largest_power)

            #Update Pg vs time plot
            if len(self.time_data) > 0 and len(self.pg_data) > 0:
                # Update the Pg vs time data with the latest time and Pg values
                self.pg_vs_time_scatter.set_offsets(np.column_stack((self.time_data, self.pg_data)))
                self.pg_vs_time_avg_line.set_data(self.time_data, self.pg_avg_data)
                self.pg_vs_time_scatter_FRT.set_offsets(np.column_stack((self.time_data, self.pg_FRT_data)))
                if self.FRT_On:
                    #For FRT Off Data set the colour to light grey and transparency to 0.5
                    #For FRT On Data set colour to pg_colours and transparency to 1.0
                    self.pg_vs_time_scatter.set_alpha(0.5)
                    self.pg_vs_time_scatter.set_color('lightgrey')
                    self.pg_vs_time_avg_line.set_alpha(0.5)
                    self.pg_vs_time_avg_line.set_color('lightgrey')
                    self.pg_vs_time_scatter_FRT.set_alpha(1.0)
                    self.pg_vs_time_scatter_FRT.set_color(self.pg_colours)
                else:
                    #For FRT Off Data set the colour to pg_colours and transparency to 1.0
                    #For FRT On Data set colour to light grey and transparency to 0.5
                    self.pg_vs_time_scatter.set_alpha(1.0)
                    self.pg_vs_time_scatter.set_color(self.pg_colours)
                    self.pg_vs_time_avg_line.set_alpha(1.0)
                    self.pg_vs_time_avg_line.set_color(self.pg_colours[-1])
                    self.pg_vs_time_scatter_FRT.set_alpha(0.5)
                    self.pg_vs_time_scatter_FRT.set_color('lightgrey')
                                
                # Update limits only if necessary
                largest_time = max(self.time_data)
                min_time = min(self.time_data)
                self.ax_pg_vs_time.set_xlim(min_time, largest_time)
                
                largest_power = max(self.pg_data)
                largest_yscale = self.ax_pg_vs_time.get_ylim()[1]
                if largest_power > largest_yscale or largest_power<0.8*largest_yscale:
                    self.ax_pg_vs_time.set_ylim(0, 1.05*largest_power)
                
                
        # Use FuncAnimation without blitting
        ani = FuncAnimation(
            self.fig,
            update,
            interval=1,  # Update interval in milliseconds
            cache_frame_data=False,
        )

        batch_size = 10  # Number of points to plot at once
        # Start the event loop
        
        offset = 0
        time = 0
        offset_step = 0.10705123420082341+9.490357641929459e-05
        while True:
                            
            batch = []
            # Get the latest values from the queue
            for _ in range(batch_size):
                data = await queue.get()
                batch.append(data)
            
            #Process the batch
            for data in batch:
                detuning = data["Detuning"]
                colour = self.Plotting_Colour
                pg = data["Pg"]
                detuning_FRT = data["Detuning FRT"]
                pg_FRT = data["Pg FRT"]
                if time >= data["Time"]:
                    offset += offset_step
                time = data["Time"]+offset
                pg_avg = data["Pg Avg"]

                # Append the new data to the circular buffers
                self.pg_colours.append(colour)
                self.detuning_data.append(detuning)
                self.pg_data.append(pg)
                self.detuning_FRT_data.append(detuning_FRT)
                self.pg_FRT_data.append(pg_FRT)
                self.time_data.append(time)
                self.pg_avg_data.append(pg_avg)
            # Force Matplotlib to redraw the canvas
            self.fig.canvas.draw_idle()
            # Allow matplotlib to update the plot
            plt.pause(0.01)
            await asyncio.sleep(0)

