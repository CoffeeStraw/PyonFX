"""
Tutorial: Creating Outputs with PyonFX

This tutorial covers the basic workflow to produce a new subtitle output:
• Loading and parsing an ASS file
• Copying and modifying an existing subtitle line
• Writing the modified line to the output

Exercise:
• Try changing the text of the copied line.
"""

from pyonfx import Ass

# Load the input ASS file and get the data
io = Ass("../ass/hello_world.ass")
meta, styles, lines = io.get_data()

# Create a copy of the first line for the output
output_line = lines[0].copy()

# Modify the text of the output line
output_line.text = "I am a new line lasting 1 second!"  # Change the text

# Write the line to the output file
io.write_line(output_line)

# Save the output file
io.save()

# Open the output in Aegisub
io.open_aegisub()

# COMMENTS TO BE REMOVED ONCE THE TUTORIAL IS PUBLISHED:
# Be sure to mention in the tutorial that if you don't specify output_file it will default to "output.ass"
# Be sure to mention that the output file is saved in the same directory as the script
# Be sure to mention that by default the output file will have all original lines commented out (controllable with the keep_original parameter)
