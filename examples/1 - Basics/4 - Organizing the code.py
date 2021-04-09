"""
Time to manage the effect creation process.
If we want to take things further, it is better to structure our code.

In this example, you will see how generally an effect should be structured.
You could use this file as a template for your future effects.
Line manipulation and output was outsourced to functions, which are called
by passing the original line and a copy, on which you will work on.
You can order every effect to a function.

Lines with alignment over than or equal at 7 will be our romaji lines,
the ones with alignment less than or equal at 3 will be our subtitle (translation) lines,
the others (4, 5, 6) will be meant for vertical kanji.

If you have seen the documentation of Ass class, you should have already seen that
it contains a vertical_kanji parameter, that will automatically calculate vertical positioning
for lines with alignment equal at 4, 5 or 6. If you don't want to let pyon automatically position
kanji in vertical alignment, you can specify this parameter to False.

Note that this code will not do anything, because there is nothing written in the romaji, kanji, sub functions.
We will create our first effect in the next section: 2 - Beginner
"""
from pyonfx import *

io = Ass("in.ass")
meta, styles, lines = io.get_data()


def romaji(line, l):
    # You will write here :D
    pass


def kanji(line, l):
    # You will write here :)
    pass


def sub(line, l):
    # You will write here :P
    pass


for line in lines:
    # Generating lines
    if line.styleref.alignment >= 7:
        romaji(line, line.copy())
    elif line.styleref.alignment >= 4:
        kanji(line, line.copy())
    else:
        sub(line, line.copy())

io.save()
io.open_aegisub()
