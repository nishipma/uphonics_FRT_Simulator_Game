import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame.midi
import asyncio
from event_system import AsyncEventSystem

class MidiDriver:
    def __init__(self, input_variables, event_system):
        self.event_system = event_system
        self.input_variables = input_variables
        self.midi_mappings = {
            36: "FoM",  # Slider 1 -> FoM
            37: "tuning_range",  # Slider 2 -> tuning_range
            38: "uphonics_range",  # Slider 4 -> microphonics_range
            39: "Qe",  # Slider 3 -> Qe
            40: "FRT_On",  # Button 1 -> FRT On
        }

    def process_midi_input(self, status, cc, value):
        """
        Process a MIDI message and update the corresponding input variable.
        :param status: The MIDI status byte (e.g., 176 for CC, 144 for Note On).
        :param cc: The MIDI CC number or Note number.
        :param value: The MIDI CC value (0-127) or Note velocity.
        """
        if status == 176:  # Control Change message
            if cc in self.midi_mappings:
                variable = self.midi_mappings[cc]
                min_val, max_val = self.input_variables[variable]['range']
                # Update the variable value (linear or logarithmic scaling)
                if variable == 'Qe':
                    new_value = min_val * (max_val / min_val) ** (value / 127)
                else:
                    new_value = min_val + (value / 127) * (max_val - min_val)

                # Check if the value has changed
                if self.input_variables[variable]['value'] != new_value:
                    self.input_variables[variable]['value'] = new_value
                    print(f"Updated {variable}: {new_value}")
                                                          
        elif status == 144:  # Note On message
            # Handle FRT On/Off switch
            value = 1 if value > 0 else 0
            if cc in self.midi_mappings:
                variable = self.midi_mappings[cc]
                if self.input_variables[variable]['value'] != value:
                    self.input_variables[variable]['value'] = value
                    print(f"Updated {variable}: {value}")
                    

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
                    for event in midi_events:
                        data = event[0]
                        status, cc, value = data[0], data[1], data[2]
                        self.process_midi_input(status, cc, value)
                        # Publish the "input_variable_changed" event
                        await self.event_system.trigger_event("input variables changed")
                                
                await asyncio.sleep(0.016)  # Yield control to the event loop

        finally:
            midi_input.close()
            midi_output.close()
            pygame.midi.quit()



# def update_calculated_variables(self):
#     """Update calculated variables based on the current input variables."""
#     #update the colour
#     current_time = time.time()
#     if current_time - self.last_update_time > 0.2:  # Check if 0.2 seconds have passed
#         self.calculated_variables['Plotting_Colour'] = self.get_next_color()
#         self.last_update_time = current_time
#     #update the calculated variables
#     self.calculated_variables['Qe_opt'] = w0/self.input_variables['uphonics_range']
#     self.calculated_variables['QFRT'] = self.input_variables['FoM']*f0/self.input_variables['tuning_range']
#     self.calculated_variables['Qe_opt_FRT'] = 1 / (1 / Q0 + 1 / self.calculated_variables['QFRT'])
#     self.calculated_variables['QL'] = 1 / (1 / self.input_variables['Qe'] + 1 / Q0)
#     self.calculated_variables['QL_FRT'] = 1 / (1 / self.input_variables['Qe'] + 1 / Q0 + 1 / self.calculated_variables['QFRT'])
