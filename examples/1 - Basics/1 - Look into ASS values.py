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

io = Ass("in.ass")
meta, styles, lines = io.get_data()

print(meta)
print("▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀")
print(styles)
print("▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀")
print(lines)
