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
    def __init__(self, variables, csv_file):
        self.variables = variables
        self.csv_file = csv_file
        self.detuning_time_generator = self._detuning_time_generator()

    @property
    def uphonics_range(self):
        """Dynamically retrieve the value of uphonics_range from variables."""
        return self.variables['uphonics_range']['value']
    
    @property
    def Qe(self):
        """Dynamically retrieve the value of Qe from variables."""
        return self.variables['Qe']['value']
    
    @property
    def tuning_range(self):
        """Dynamically retrieve the value of tuning_range from variables."""
        return self.variables['tuning_range']['value']
    
    @property
    def FRT_On(self):
        """Dynamically retrieve the value of FRT_On from variables."""
        return self.variables['FRT On']['value']
    
    @property
    def FoM(self):
        """Dynamically retrieve the value of FoM from variables."""
        return self.variables['FoM']['value']
    
    @property
    def QFRT(self):
        """Calculate QFRT based on the current variables."""
        return self.FoM*f0/self.tuning_range
    
    @property
    def QL(self):
        """Calculate QL based on the current variables."""
        return 1 / (1 / self.Qe + 1 / Q0)

    @property
    def QL_FRT(self):
        """Calculate QL_FRT based on the current variables."""
        return 1 / (1 / self.Qe + 1 / Q0 + 1 / self.QFRT)

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

    async def start_async(self, queue):
        # Placeholder for the main loop of the kernel
        while True:
            time, detuning, detuning_FRT = self.DeltaOmega_t()
            Pgen, Pgen_FRT = self.Pg(detuning, detuning_FRT)
            await queue.put({"Time": time, "Detuning": detuning, "Pg": Pgen, "Detuning FRT": detuning_FRT, "Pg_FRT": Pgen_FRT})
            await asyncio.sleep(0)  # Simulate some processing delay
            