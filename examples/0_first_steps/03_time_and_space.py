"""
Tutorial: Lines' Positioning and Timing

In this tutorial, you will explore the various properties of a Line object:
• Positioning: understand the horizontal and vertical position properties,
               and how to use them combined with alignments to position subtitles precisely on the screen
• Timing: understand the start_time and end_time properties,
          and how to use them to control the timing of subtitles

Exercise:
• Try changing the timing and/or position of the copied line and check how the output changes.
"""

from pyonfx import Ass

# Load the input ASS file and get the data
io = Ass("../ass/hello_world.ass")
meta, styles, lines = io.get_data()

# Create a copy of the first line for the output
line = lines[0]
l = line.copy()

# an1 - Bottom Left → use line.left, line.bottom
l.start_time = 0
l.end_time = 500
l.text = "{\\an1\\pos(%.3f,%.3f)\\1c&H4B19E6&}%s" % (line.left, line.bottom, line.text)
io.write_line(l)

# an2 - Bottom Center → use line.center, line.bottom
l.start_time = 500
l.end_time = 1000
l.text = "{\\an2\\pos(%.3f,%.3f)\\1c&H4BB43C&}%s" % (
    line.center,
    line.bottom,
    line.text,
)
io.write_line(l)

# an3 - Bottom Right → use line.right, line.bottom
l.start_time = 1000
l.end_time = 1500
l.text = "{\\an3\\pos(%.3f,%.3f)\\1c&H19E1FF&}%s" % (line.right, line.bottom, line.text)
io.write_line(l)

# an4 - Middle Left → use line.left, line.middle
l.start_time = 1500
l.end_time = 2000
l.text = "{\\an4\\pos(%.3f,%.3f)\\1c&HD86343&}%s" % (line.left, line.middle, line.text)
io.write_line(l)

# an5 - Center → use line.center, line.middle (or just line.x, line.y)
l.start_time = 2000
l.end_time = 2500
l.text = "{\\an5\\pos(%.3f,%.3f)\\1c&H3182F5&}%s" % (
    line.center,
    line.middle,
    line.text,
)
io.write_line(l)

# an6 - Middle Right → use line.right, line.middle
l.start_time = 2500
l.end_time = 3000
l.text = "{\\an6\\pos(%.3f,%.3f)\\1c&HB41E91&}%s" % (line.right, line.middle, line.text)
io.write_line(l)

# an7 - Top Left → use line.left, line.top
l.start_time = 3000
l.end_time = 3500
l.text = "{\\an7\\pos(%.3f,%.3f)\\1c&HF0F046&}%s" % (line.left, line.top, line.text)
io.write_line(l)

# an8 - Top Center → use line.center, line.top
l.start_time = 3500
l.end_time = 4000
l.text = "{\\an8\\pos(%.3f,%.3f)\\1c&HE632F0&}%s" % (line.center, line.top, line.text)
io.write_line(l)

# an9 - Top Right → use line.right, line.top
l.start_time = 4000
l.end_time = 4500
l.text = "{\\an9\\pos(%.3f,%.3f)\\1c&H3CF5D2&}%s" % (line.right, line.top, line.text)
io.write_line(l)

# Save the output and open in Aegisub
io.save()
io.open_aegisub()
