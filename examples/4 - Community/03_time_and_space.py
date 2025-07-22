"""
Tutorial: Mastering lines' Positioning and Timing

In this tutorial, you will explore the various properties of a Line object:
• Positioning: understand the horizontal and vertical position properties,
               and how to use them combined with alignments to position subtitles precisely on the screen.
• Timing: understand the start_time, end_time, and duration properties,
          and how to use them to control the timing of subtitles.

Exercise:
• Try changing the timing and/or position of the copied line and check how the output changes.
"""

from pyonfx import Ass

# Load the input file
io = Ass("../ass/hello_world.ass")
meta, styles, lines = io.get_data()

# Process each line to show different alignment/position combinations
for line in lines:
    # Store the original text, as it will be overwritten
    l = line.copy()

    # an1 - Bottom Left → use line.left, line.bottom
    l.text = "{\\an1\\pos(%d,%d)}%s" % (line.left, line.bottom, line.text)
    io.write_line(l)

    # an2 - Bottom Center → use line.center, line.bottom
    l.text = "{\\an2\\pos(%d,%d)}%s" % (line.center, line.bottom, line.text)
    io.write_line(l)

    # an3 - Bottom Right → use line.right, line.bottom
    l.text = "{\\an3\\pos(%d,%d)}%s" % (line.right, line.bottom, line.text)
    io.write_line(l)

    # an4 - Middle Left → use line.left, line.middle
    l.text = "{\\an4\\pos(%d,%d)}%s" % (line.left, line.middle, line.text)
    io.write_line(l)

    # an5 - Center → use line.center, line.middle (or just line.x, line.y)
    l.text = "{\\an5\\pos(%d,%d)}%s" % (line.center, line.middle, line.text)
    io.write_line(l)

    # an6 - Middle Right → use line.right, line.middle
    l.text = "{\\an6\\pos(%d,%d)}%s" % (line.right, line.middle, line.text)
    io.write_line(l)

    # an7 - Top Left → use line.left, line.top
    l.text = "{\\an7\\pos(%d,%d)}%s" % (line.left, line.top, line.text)
    io.write_line(l)

    # an8 - Top Center → use line.center, line.top
    l.text = "{\\an8\\pos(%d,%d)}%s" % (line.center, line.top, line.text)
    io.write_line(l)

    # an9 - Top Right → use line.right, line.top
    l.text = "{\\an9\\pos(%d,%d)}%s" % (line.right, line.top, line.text)
    io.write_line(l)

# Save the output and open in Aegisub
io.save()
io.open_aegisub()
