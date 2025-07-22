"""
Tutorial: Exploring ASS Structure

In this tutorial, you'll learn how PyonFX reads an ASS file and converts it into structured objects:
• Meta data about the subtitle file
• Styles that define appearance
• Lines that are further broken down into words, syllables, and characters

Exercise:
• Experiment parsing a different ASS file to see how the printed values change.
"""

from pyonfx import Ass

# Load the input ASS file and get the data
io = Ass("../ass/hello_world.ass")
meta, styles, lines = io.get_data()

# Print the META object
print("📋 META OBJECT:")
print(f"{meta}\n")

# Print the STYLES dictionary
print("🎨 STYLES:")
for style_name, style in styles.items():
    print(f'"{style_name}": {style}\n')

# Print the LINES list
print("📝 LINES:")
for line in lines:
    print(f"{line}\n")

# Print the first word of the first line
print("🔤 FIRST WORD OF THE FIRST LINE:")
print(f"{lines[0].words[0]}\n")

# Print the first syllable of the first line
print("🎤 FIRST SYLLABLE OF THE FIRST LINE:")
print(f"{lines[0].syls[0]}\n")

# Print the first char of the first line
print("🅰️  FIRST CHAR OF THE FIRST LINE:")
print(f"{lines[0].chars[0]}\n")
