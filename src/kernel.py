from display import Display
from midi_driver import MidiDriver

def main():
    # Initialize variables
    variables = {
        'FoM': 20,
        'uphonics_range': 20,
        'Qe': 16,
        'tuning_range': 25
    }

    # Initialize display and MIDI driver
    display = Display(variables)
    midi_driver = MidiDriver(variables)

    # Start MIDI driver (keyboard listener)
    midi_driver.start()

    # Start the live plot
    display.start()

if __name__ == "__main__":
    main()