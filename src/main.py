from display import Display
from midi_driver import MidiDriver
import asyncio

async def main():
    # Initialize variables
    variables = {
        'FoM': 20,
        'uphonics_range': 20,
        'Qe': 16,
        'tuning_range': 25,
        'FRT On': 0,
    }

    # Initialize display and MIDI driver
    display = Display(variables)
    midi_driver = MidiDriver(variables)

    # Run MIDI driver and display concurrently
    await asyncio.gather(
        midi_driver.start_async(),
        display.start_async()
    )

if __name__ == "__main__":
    asyncio.run(main())