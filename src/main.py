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
    variables = {
        'FoM': {'value': 20, 'range': variable_ranges['FoM']},
        'uphonics_range': {'value': 20, 'range': variable_ranges['uphonics_range']},
        'Qe': {'value': 10**6, 'range': variable_ranges['Qe']},
        'tuning_range': {'value': 25, 'range': variable_ranges['tuning_range']},
        'FRT On': {'value':0}
    }

    control_variables = {'Plotting_Colour': 'blue'}

    # Path to the CSV file
    csv_file = os.path.join("..", "data", "detuning.csv")

    # Initialize display and MIDI driver
    display = Display(variables,control_variables)
    midi_driver = MidiDriver(variables,control_variables)
    kernel = Kernel(variables, csv_file)

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