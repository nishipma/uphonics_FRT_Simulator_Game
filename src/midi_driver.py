import pygame.midi
import asyncio

class MidiDriver:
    def __init__(self, variables):
        self.variables = variables
        self.midi_mappings = {
            36: "FoM",  # Slider 1 -> FoM
            37: "uphonics_range",  # Slider 2 -> uphonics_range
            38: "Qe",  # Slider 3 -> Qe
            39: "tuning_range",  # Slider 4 -> tuning_range
            40: "FRT On",  # Button 1 -> FRT On
        }

    async def start_async(self):
        """Asynchronous MIDI event listener."""
        pygame.midi.init()
        input_id = pygame.midi.get_default_input_id()
        if input_id == -1:
            print("No MIDI input devices found.")
            return

        print(f"Listening to MIDI input on device ID: {input_id}")
        midi_input = pygame.midi.Input(input_id)

        # Initialize the MIDI output device
        output_id = 3  # Replace with the correct device ID for your output device
        try:
            midi_output = pygame.midi.Output(output_id)
        except Exception as e:
            print(f"Failed to open MIDI output device: {e}")
            return    

        try:
            # Main loop to read MIDI events
            while True:
                if midi_input.poll():
                    midi_events = midi_input.read(10)
                    for event in midi_events:
                        data = event[0]
                        status, cc, value = data[0], data[1], data[2]
                        if status == 176:  # Control Change message
                            if cc in self.midi_mappings:
                                variable = self.midi_mappings[cc]
                                self.variables[variable] = value * 100 / 127
                                print(f"Updated {variable}: {self.variables[variable]}")
                        if status == 144:
                            # Switch FRT On/Off
                            value = 1 if value > 0 else 0
                            if cc in self.midi_mappings:
                                variable = self.midi_mappings[cc]
                                if self.variables[variable] != value:
                                    self.variables[variable] = value
                                    print(f"Updated {variable}: {self.variables[variable]}")
                                
                await asyncio.sleep(0.01)  # Yield control to the event loop

        finally:
            midi_input.close()
            midi_output.close()
            pygame.midi.quit()

# from pynput import keyboard

# class MidiDriver:
#     def __init__(self, variables, step=1):
#         self.variables = variables
#         self.step = step
#         self.key_mappings = {
#             "a": "FoM",  # Increase FoM
#             "z": "FoM",  # Decrease FoM
#             "s": "uphonics_range",  # Increase uphonics_range
#             "x": "uphonics_range",  # Decrease uphonics_range
#             "d": "Qe",  # Increase Qe
#             "c": "Qe",  # Decrease Qe
#             "f": "tuning_range",  # Increase tuning_range
#             "v": "tuning_range",  # Decrease tuning_range
#         }

#     def on_press(self, key):
#         try:
#             # Check if the key is mapped
#             if hasattr(key, 'char') and key.char in self.key_mappings:
#                 variable = self.key_mappings[key.char]
#                 if key.char in "asdf":  # Increase keys
#                     self.variables[variable] += self.step
#                 elif key.char in "zxcv":  # Decrease keys
#                     self.variables[variable] -= self.step

#                 # Print updated variables
#                 print(f"Updated variables: {self.variables}")
#         except AttributeError:
#             # Handle special keys (not used here)
#             pass

#     def start(self):
#         """Start listening to keyboard events."""
#         listener = keyboard.Listener(on_press=self.on_press)
#         listener.start()