import csv
import json
import os
import asyncio
import numpy as np
import time
import matplotlib.cm as cm

#detuning_offset
detuning_offset = 0.034688375

# Construct the path to the config file
config_path = os.path.join("..", "config", "config.json")

# Load the config.json file with error handling
try:
    with open(config_path, "r", encoding="utf-16") as config_file:
        content = config_file.read().encode("utf-8").decode("utf-8")  # Remove BOM by re-encoding
        config = json.loads(content)
except FileNotFoundError:
    print(f"Error: Config file not found at {config_path}")
    config = {}
except json.JSONDecodeError as e:
    print(f"Error: Failed to parse JSON file at {config_path}: {e}")
    config = {}

# Access the variables from the config file
f0 = config["constants"]["f0"]
w0 = 2*np.pi*f0
Vc = config["constants"]["Vc"]
Q0 = config["constants"]["Q0"]
RQ = config["constants"]["RQ"]


class Kernel:
    def __init__(self, input_variables, calculated_variables, csv_file, event_system):
        self.input_variables = input_variables
        self.calculated_variables = calculated_variables
        self.csv_file = csv_file
        self.event_system = event_system
        self.detuning_time_generator = self._detuning_time_generator()
        self.input_variable_queue = event_system.add_listener("input variables changed")
        self.last_update_time = time.time()
        self.color_index = 0

        #Cache for input variables
        self._cached_input_variables = {}
        self._cache_valid =False
        
    def _invalidate_cache(self):
        """Invalidate the cache when input variables change."""
        self._cache_valid = False

    def _get_cached_input_variables(self, key):
        """Retrieve a cached value or recalculate it if the cache is invalid."""
        if not self._cache_valid:
            # Recalculate the value and update the cache
            self._recalculate_variables()
        return self._cached_input_variables[key]

    def _get_next_color(self):
        """Generate the next color from a color wheel."""
        num_colors = 10  # Number of distinct colors
        colormap = cm.get_cmap('hsv', num_colors)  # Use the HSV color wheel
        color = colormap(self.color_index % num_colors)  # Get the next color
        self.color_index += 1
        # Convert RGBA to a hex color string
        return '#{:02x}{:02x}{:02x}'.format(
            int(color[0] * 255), int(color[1] * 255), int(color[2] * 255)
        )

    def _recalculate_variables(self):
        """Recalculate all input and calculated variables and update the cache."""
        for key in self.input_variables:
            # Recalculate the input variable
            value = self.input_variables[key]['value']
            self._cached_input_variables[key] = value
        # Recalculate the calculated variables
        current_time = time.time()
        if current_time - self.last_update_time > 0.2:  # Check if 0.2 seconds have passed
            self.calculated_variables['Plotting_Colour'] = self._get_next_color()
            self.last_update_time = current_time
        #update the calculated variables
        self.calculated_variables['Qe_opt'] = w0/self._cached_input_variables['uphonics_range']
        self.calculated_variables['QFRT'] = self._cached_input_variables['FoM']*f0/self._cached_input_variables['tuning_range']
        self.calculated_variables['Qe_opt_FRT'] = 1 / (1 / Q0 + 1 / self.calculated_variables['QFRT'])
        self.calculated_variables['QL'] = 1 / (1 / self._cached_input_variables['Qe'] + 1 / Q0)
        self.calculated_variables['QL_FRT'] = 1 / (1 / self._cached_input_variables['Qe'] + 1 / Q0 + 1 / self.calculated_variables['QFRT'])

        # Notify other components that calculated variables have changed
        asyncio.create_task(self.event_system.trigger_event("calculated variables changed", self.calculated_variables))

        # Mark the cache as valid
        self._cache_valid = True

    async def _listen_for_input_changes(self):
        """Listen for changes in input variables and invalidate the cache."""
        while True:
            # Wait for a change in input variables
            await self.input_variable_queue.get()
            # Invalidate the cache when a change is detected
            self._invalidate_cache()
    
    @property
    def uphonics_range(self):
        """Dynamically retrieve the value of uphonics_range from variables."""
        return self._get_cached_input_variables('uphonics_range')
    
    @property
    def Qe(self):
        """Dynamically retrieve the value of Qe from variables."""
        return self._get_cached_input_variables('Qe')
    
    @property
    def tuning_range(self):
        """Dynamically retrieve the value of tuning_range from variables."""
        return self._get_cached_input_variables('tuning_range')
    
    
    @property
    def FRT_On(self):
        """Dynamically retrieve the value of FRT_On from variables."""
        return self._get_cached_input_variables('FRT_On')
    
    @property
    def FoM(self):
        """Dynamically retrieve the value of FoM from variables."""
        return self._get_cached_input_variables('FoM')
    
    @property
    def QL(self):
        """Calculate QL based on the current variables."""
        return self.calculated_variables['QL']

    @property
    def QL_FRT(self):
        """Calculate QL_FRT based on the current variables."""
        return self.calculated_variables['QL_FRT']
    
    def _get_state(self):
        """Return the current state of the midi controls except FRT_On."""
        state = (self.uphonics_range, self.Qe, self.tuning_range, self.FoM)
        return state

    def _detuning_time_generator(self):
        """Generator to yield detuning and time pairs from the CSV file."""
        while True:
            with open(self.csv_file, "r") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    detuning = float(row["Detuning [Hz]"])
                    time = float(row["time"])
                    yield (time,detuning)

    def IgeiPhi(self, detuning, detuning_FRT):
        """Calculate IgeiPhi based on the current variables."""
        real_brack = Vc / (2 * RQ * self.QL)
        real_brack_FRT = Vc / (2 * RQ * self.QL_FRT)
        imag_brack = 1j * Vc * detuning / (w0 * RQ)
        imag_brack_FRT = 1j * Vc * detuning_FRT / (w0 * RQ)
        Ig = real_brack + imag_brack
        Ig_FRT = real_brack_FRT + imag_brack_FRT
        return Ig, Ig_FRT
    
    def Pg(self,detuning,detuning_FRT):
        """Calculate Pg based on the current variables."""
        Ig, Ig_FRT = self.IgeiPhi(detuning,detuning_FRT)
        Pg = self.Qe*RQ*np.abs(Ig)**2/2
        Pg_FRT = self.Qe*RQ*np.abs(Ig_FRT)**2/2
        return Pg, Pg_FRT

    def DeltaOmega_t(self):
        """Get the next detuning and time pair from the generator."""
        t, detuning = next(self.detuning_time_generator)
        # Apply self.uphonics_range dynamically here
        detuning = self.uphonics_range * (detuning + detuning_offset) / 2
        if np.abs(detuning) > self.tuning_range/2:
            detuning_FRT = np.sign(detuning)*(np.abs(detuning)-self.tuning_range/2)
        else:
            detuning_FRT = 0
        
        return t, detuning, detuning_FRT
    
    def AvergaePower(self,Pgen,Pgen_FRT):
        """Calculate the avergae powers"""
        # Initialize/reset state tracking and accumulators
        if not hasattr(self, "_state") or not hasattr(self, "_pg_sum"):
            self._state = self._get_state()
            self._pg_sum = 0
            self._pg_frt_sum = 0
            self._count = 0
            
        # Check if any property has changed
        current_state = self._get_state()
        if current_state != self._state:
            # Reset accumulators if state has changed
            self._state = current_state
            self._pg_sum = 0
            self._pg_frt_sum = 0
            self._count = 0

        # Update accumulators
        self._pg_sum += Pgen
        self._pg_frt_sum += Pgen_FRT
        self._count += 1

        # Calculate averages
        avg_pg = self._pg_sum / self._count
        avg_pg_frt = self._pg_frt_sum / self._count

        return avg_pg, avg_pg_frt
    
    async def start_async(self, results_queue):
        # Placeholder for the main loop of the kernel
        while True:
            time, detuning, detuning_FRT = self.DeltaOmega_t()
            Pgen, Pgen_FRT = self.Pg(detuning, detuning_FRT)
            Pg_Avg, Pg_FRT_Avg = self.AvergaePower(Pgen, Pgen_FRT)
            await results_queue.put({"Time": time,
                             "Detuning": detuning, "Pg": Pgen,
                             "Detuning FRT": detuning_FRT, "Pg FRT": Pgen_FRT,
                             "Pg Avg": Pg_Avg, "Pg FRT Avg": Pg_FRT_Avg,
                             })
            await asyncio.sleep(0)  # Simulate some processing delay
            