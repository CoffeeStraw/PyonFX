"""
This script visualizes which ASS values you got from input ASS file.

First of all you need to create an Ass object, which will help you to manage
input/output. Once created, it will automatically extract all the informations
from the input .ass file.

For more info about the use of Ass class:
https://pyonfx.readthedocs.io/en/latest/reference/ass%20core.html#pyonfx.ass_core.Ass

By executing this script, you'll discover how ASS contents,
like video resolution, styles, lines etc. are stored into objects and lists.
It's important to understand it, because these Python lists and objects
are exactly the values you'll be working with the whole time to create KFX.

Don't worry about the huge output, there are a lot of information
even in a small input file like the one in this folder.

You can find more info about each object used to represent the input .ass file here:
https://pyonfx.readthedocs.io/en/latest/reference/ass%20core.html
"""

from pyonfx import *

# Open the input ASS file and get the data
#     Note that by default, PyonFX will show a progress bar when iterating over lines.
#     In this example, we'll disable it through progress=False to avoid cluttering the output.
io = Ass("in.ass", progress=False)
meta, styles, lines = io.get_data()

# Print the META object
print("📋 META OBJECT:")
print(f"    {meta}\n")

print("─" * 80 + "\n")  # ──────────────

# Print the STYLES dictionary
print("🎨 STYLES:")
for style_name, style in styles.items():
    print(f'    "{style_name}":')
    print(f"        {style}\n")

print("─" * 80 + "\n")  # ──────────────

# Print the LINES list
print("📝 LINES:")
for line in lines:
    print(f"    {line}\n")

print("─" * 80 + "\n")  # ──────────────

# Print the first word of the first line
print("🔤 FIRST WORD OF THE FIRST LINE:")
print(f"    {lines[0].words[0]}\n")

print("─" * 80 + "\n")  # ──────────────

# Print the first syllable of the first line
print("🎤 FIRST SYLLABLE OF THE FIRST LINE:")
print(f"    {lines[0].syls[0]}\n")

print("─" * 80 + "\n")  # ──────────────

# Print the first char of the first line
print("🅰️  FIRST CHAR OF THE FIRST LINE:")
print(f"    {lines[0].chars[0]}\n")
