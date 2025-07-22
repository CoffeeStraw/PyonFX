"""
Tutorial: Understanding Text Segmentation

This tutorial explains how PyonFX segments a subtitle line into words, syllables, and characters.

For each segment type, we show that:
• Each entity has time and position properties (same as Line)
• Each entity has an index property (same as Line)

Exercise:
• Adjust timing windows, and try to add a different ASS tag for each separate entity.
"""

from pyonfx import Ass

# Load the input ASS file
io = Ass("../ass/hello_world.ass")
meta, styles, lines = io.get_data()

# Use the first line from the file
line = lines[0]
l = line.copy()

# Define color codes for red and blue
RED = "&HFF0000&"
BLUE = "&H0000FF&"

# Process words: words start to appear from 0ms
all_words_start = 0
for word in line.words:
    color = RED if (word.i % 2 == 0) else BLUE
    l.start_time = all_words_start + word.start_time
    l.end_time = all_words_start + word.end_time
    l.text = "{\\an5\\pos(%.3f,%.3f)\\1c%s}%s" % (
        word.center,
        word.middle,
        color,
        word.text,
    )
    io.write_line(l)

# Process syllables: syllables start to appear from 3000ms
all_syls_start = 3000
for syl in line.syls:
    color = RED if (syl.i % 2 == 0) else BLUE
    l.start_time = all_syls_start + syl.start_time
    l.end_time = all_syls_start + syl.end_time
    l.text = "{\\an5\\pos(%.3f,%.3f)\\1c%s}%s" % (
        syl.center,
        syl.middle,
        color,
        syl.text,
    )
    io.write_line(l)

# Process characters: characters start to appear from 5000ms
all_chars_start = 5000
for char in line.chars:
    color = RED if (char.i % 2 == 0) else BLUE
    l.start_time = all_chars_start + char.start_time
    l.end_time = all_chars_start + char.end_time
    l.text = "{\\an5\\pos(%.3f,%.3f)\\1c%s}%s" % (
        char.center,
        char.middle,
        color,
        char.text,
    )
    io.write_line(l)

# Save the output and open in Aegisub
io.save()
io.open_aegisub()
