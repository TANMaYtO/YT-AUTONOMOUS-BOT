"""Node 3 — Image Picker.

Selects character images from the local pre-generated library
in assets/characters/{name}/.

For each character in the script, randomly picks one image file
from their folder. Validates the image file (PNG magic bytes,
minimum file size) before accepting.

Writes to state:
    character_a_image, character_b_image
"""

# import logging
# import random
# from pathlib import Path
#
# from agent.state import VideoState, validate_state_for_node
