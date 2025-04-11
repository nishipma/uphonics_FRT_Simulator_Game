import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame.midi
import asyncio
import matplotlib.cm as cm
import time

class MidiDriver:
    def __init__(self, variables,control_variables):
        self.plotting_colour = control_variables['Plotting_Colour']
        self.last_update_time = 0  # Track the last time the color was updated
        self.color_index = 0  # Index for the color wheel
        
        self.variables = variables
        self.midi_mappings = {
            36: "FoM",  # Slider 1 -> FoM
            37: "uphonics_range",  # Slider 2 -> uphonics_range
            38: "tuning_range",  # Slider 4 -> tuning_range
            39: "Qe",  # Slider 3 -> Qe
            40: "FRT On",  # Button 1 -> FRT On
        }

    def get_next_color(self):
        """Generate the next color from a color wheel."""
        num_colors = 100  # Number of distinct colors
        colormap = cm.get_cmap('hsv', num_colors)  # Use the HSV color wheel
        color = colormap(self.color_index % num_colors)  # Get the next color
        self.color_index += 1
        # Convert RGBA to a hex color string
        return '#{:02x}{:02x}{:02x}'.format(
            int(color[0] * 255), int(color[1] * 255), int(color[2] * 255)
        )
    
    async def start_async(self):
        """Asynchronous MIDI event listener."""
        # Initialize Pygame MIDI
        pygame.midi.init()
        input_id = pygame.midi.get_default_input_id()
        if input_id == -1:
            print("No MIDI input devices found.")
            return

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
                    #update the colour
                    current_time = time.time()
                    if current_time - self.last_update_time > 0.2:  # Check if 0.2 seconds have passed
                        self.plotting_colour = self.get_next_color()
                        self.last_update_time = current_time
                    for event in midi_events:
                        data = event[0]
                        status, cc, value = data[0], data[1], data[2]
                        if status == 176:  # Control Change message
                            if cc in self.midi_mappings:
                                variable = self.midi_mappings[cc]
                                min_val, max_val = self.variables[variable]['range']
                                self.variables[variable]['value'] = min_val + (value / 127) * (max_val - min_val)
                                print(f"Updated {variable}: {self.variables[variable]['value']}")
                        if status == 144:
                            # Switch FRT On/Off
                            value = 1 if value > 0 else 0
                            if cc in self.midi_mappings:
                                variable = self.midi_mappings[cc]
                                if self.variables[variable]['value'] != value:
                                    self.variables[variable]['value'] = value
                                    print(f"Updated {variable}: {self.variables[variable]['value']}")
                                
                await asyncio.sleep(0.016)  # Yield control to the event loop

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