"""
This script creates your first dialog line in "Output.ass", which is
the default name for the output that will contains our original dialog lines (commented) + our new generated lines.

The magic function is write_line(), a class function of Ass
which converts a dialog line of class Line back to text form and appends it to "Output.ass".
For more info: https://pyonfx.readthedocs.io/en/latest/reference/ass%20core.html#pyonfx.ass_core.Ass.write_line

To show the first manipulation, we take the first line of our input
and print it back on the output changing only the text.

It's not a good idea doing it this way because the original line text is overwritten and
for future manipulations you will not be able to take the line's original values anymore
without re parsing again the input file by creating a new Ass object.

Instead, you should always create a copy of line to save the original, we will see how in the following examples.

At the end, you have to call save() class method to actually write your output.
PyonFX will also automatically print how many lines you've written and the process duration.
For more info: https://pyonfx.readthedocs.io/en/latest/reference/ass%20core.html#pyonfx.ass_core.Ass.save

Finally, we call the open_aegisub method to open the output with Aegisub. Generally you would prefer to open it
with MPV by using the open_mpv method, but the examples'ass file do not have videos.
For more info:
- open_aegisub: https://pyonfx.readthedocs.io/en/latest/reference/ass%20core.html#pyonfx.ass_core.Ass.open_aegisub
- open_mpv: https://pyonfx.readthedocs.io/en/latest/reference/ass%20core.html#pyonfx.ass_core.Ass.open_mpv
"""
from pyonfx import *

io = Ass("in.ass")
meta, styles, lines = io.get_data()

lines[0].text = "I am a new line!"
io.write_line(lines[0])

io.save()
io.open_aegisub()
