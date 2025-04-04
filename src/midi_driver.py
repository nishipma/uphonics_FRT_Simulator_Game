from pynput import keyboard

class MidiDriver:
    def __init__(self, variables, step=1):
        self.variables = variables
        self.step = step
        self.key_mappings = {
            "a": "FoM",  # Increase FoM
            "z": "FoM",  # Decrease FoM
            "s": "uphonics_range",  # Increase uphonics_range
            "x": "uphonics_range",  # Decrease uphonics_range
            "d": "Qe",  # Increase Qe
            "c": "Qe",  # Decrease Qe
            "f": "tuning_range",  # Increase tuning_range
            "v": "tuning_range",  # Decrease tuning_range
        }

    def on_press(self, key):
        try:
            # Check if the key is mapped
            if hasattr(key, 'char') and key.char in self.key_mappings:
                variable = self.key_mappings[key.char]
                if key.char in "asdf":  # Increase keys
                    self.variables[variable] += self.step
                elif key.char in "zxcv":  # Decrease keys
                    self.variables[variable] -= self.step

                # Print updated variables
                print(f"Updated variables: {self.variables}")
        except AttributeError:
            # Handle special keys (not used here)
            pass

    def start(self):
        """Start listening to keyboard events."""
        listener = keyboard.Listener(on_press=self.on_press)
        listener.start()