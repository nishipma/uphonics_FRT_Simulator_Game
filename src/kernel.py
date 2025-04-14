import csv
import json
import os
import asyncio
import numpy as np

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
    def __init__(self, input_variables, calculated_variables, csv_file):
        self.input_variables = input_variables
        self.calculated_variables = calculated_variables
        self.csv_file = csv_file
        self.detuning_time_generator = self._detuning_time_generator()

    @property
    def uphonics_range(self):
        """Dynamically retrieve the value of uphonics_range from variables."""
        return self.input_variables['uphonics_range']['value']
    
    @property
    def Qe(self):
        """Dynamically retrieve the value of Qe from variables."""
        return self.input_variables['Qe']['value']
    
    @property
    def tuning_range(self):
        """Dynamically retrieve the value of tuning_range from variables."""
        return self.input_variables['tuning_range']['value']
    
    @property
    def FRT_On(self):
        """Dynamically retrieve the value of FRT_On from variables."""
        return self.input_variables['FRT On']['value']
    
    @property
    def FoM(self):
        """Dynamically retrieve the value of FoM from variables."""
        return self.input_variables['FoM']['value']
    
    @property
    def QFRT(self):
        """Calculate QFRT based on the current variables."""
        return self.calculated_variables['QFRT']
    
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
    
    async def start_async(self, queue):
        # Placeholder for the main loop of the kernel
        while True:
            time, detuning, detuning_FRT = self.DeltaOmega_t()
            Pgen, Pgen_FRT = self.Pg(detuning, detuning_FRT)
            Pg_Avg, Pg_FRT_Avg = self.AvergaePower(Pgen, Pgen_FRT)
            await queue.put({"Time": time,
                             "Detuning": detuning, "Pg": Pgen,
                             "Detuning FRT": detuning_FRT, "Pg_FRT": Pgen_FRT,
                             "Pg_Avg": Pg_Avg, "Pg_FRT_Avg": Pg_FRT_Avg,
                             })
            await asyncio.sleep(0)  # Simulate some processing delay
            