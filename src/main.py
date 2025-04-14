from display import Display
from midi_driver import MidiDriver
from kernel import Kernel
import os
import asyncio

async def main():
    print("Welcome to the microphonics FE-FRT simulator!")
    # Create the shared asyncio.Queue
    queue = asyncio.Queue(maxsize = 100)
    
    # Define default ranges for variables
    variable_ranges = {
        'FoM': (0.1, 100),
        'uphonics_range': (0, 100),
        'Qe': (10**4, 10**10),
        'tuning_range': (0.1, 100)
    }

    # Initialize variables with default values and ranges
    input_variables = {
        'FoM': {'value': 20, 'range': variable_ranges['FoM']},
        'uphonics_range': {'value': 20, 'range': variable_ranges['uphonics_range']},
        'Qe': {'value': 10**7, 'range': variable_ranges['Qe']},
        'tuning_range': {'value': 25, 'range': variable_ranges['tuning_range']},
        'FRT On': {'value':0}
    }

    calculated_variables = {
        'Plotting_Colour': '#ff0000',
        'Qe_opt': {'value': 0},
        'Qe_opt_FRT': {'value': 0},
        'QL': {'value': 0},
        'QL_FRT': {'value': 0},
    }

    # Path to the CSV file
    csv_file = os.path.join("..", "data", "detuning.csv")

    # Initialize display and MIDI driver
    display = Display(input_variables,calculated_variables)
    midi_driver = MidiDriver(input_variables,calculated_variables)
    kernel = Kernel(input_variables, calculated_variables, csv_file)

    # Run MIDI driver and display concurrently
    try:
        await asyncio.gather(
            midi_driver.start_async(),
            display.start_async(queue),
            kernel.start_async(queue)
        )
    except asyncio.CancelledError:
        print("Program stopped.")

if __name__ == "__main__":
    asyncio.run(main())