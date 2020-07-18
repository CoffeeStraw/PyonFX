"""
Let's go a bit further.

In this script we will iterate through all the lines of our .ass,
create a copy for each of them (see the reason for that in the previous example)
and finally write them back on our output with time shifted by 2000ms.

For more info about the copy method:
https://pyonfx.readthedocs.io/en/latest/reference/ass%20core.html#pyonfx.ass_core.Line.copy
"""
from pyonfx import *

io = Ass("in.ass")
meta, styles, lines = io.get_data()

for line in lines:
    l = line.copy()

    l.start_time += 2000
    l.end_time += 2000

    io.write_line(l)

io.save()
io.open_aegisub()
