"""
And here we are with our first complete effect.
As you can see, we have now filled our romaji, kanji and sub functions.

Starting from the simple one, the sub function make use of leadin and leadout times for fitting line-to-line changes.
We then construct the text of each line, giving an alignment, a position and a fad to make a soft entrance and exit.
    (Docs: https://pyonfx.readthedocs.io/en/latest/reference/ass%20core.html#pyonfx.ass_core.Line.leadin)

In the romaji function instead, we want to create an effect that works with syllables.
In order to do do that, every syllable has to be one dialog line,
so we loop through syllable entries of current line.
Using a utility provided in Utils module, all_non_empty(), we assure
that we will not work with blank syllables or syls with duration equals to zero.
    (Docs: https://pyonfx.readthedocs.io/en/latest/reference/utils.html#pyonfx.utils.Utils.all_non_empty)

In a similiar fashion to what we did in the sub function, we create a leadin and a leadout using fad tag,
then we create our first main effect by using a simple trasformation, obtaining a grow/shrink effect.

Remember to always set the layer for the line. Usually, main effects should have an higher value than leadin and leadout,
beacuse they are more important, so by doing this they will be drawn over the other effects.

For the kanji function, we are calling the same functions of romaji, but using chars instead of syls.
"""

from pyonfx import *

io = Ass("in.ass", vertical_kanji=True)
meta, styles, lines = io.get_data()


@io.track
def leadin_effect(line: Line, obj: Syllable | Char, l: Line):
    l.layer = 0
    l.start_time = line.start_time - line.leadin // 2
    l.end_time = line.start_time + obj.start_time

    tags = rf"\an5\pos({obj.center},{obj.middle})\fad({line.leadin // 2},0)"
    l.text = f"{{{tags}}}{obj.text}"

    io.write_line(l)


@io.track
def main_effect(line: Line, obj: Syllable | Char, l: Line):
    l.layer = 1
    l.start_time = line.start_time + obj.start_time
    l.end_time = line.start_time + obj.end_time

    # Original values
    c1 = line.styleref.color1
    c3 = line.styleref.color3
    fscx = line.styleref.scale_x
    fscy = line.styleref.scale_y

    # New values
    new_fscx = fscx * 1.25
    new_fscy = fscy * 1.25
    new_c1 = "&HFFFFFF&"
    new_c3 = "&HABABAB&"

    tags = (
        rf"\an5\pos({obj.center},{obj.middle})"
        rf"\t(0,{obj.duration // 3},0.5, \fscx{new_fscx}\fscy{new_fscy}\1c{new_c1}\3c{new_c3})"
        rf"\t({obj.duration // 3},{obj.duration},1.5, \fscx{fscx}\fscy{fscy}\1c{c1}\3c{c3})"
    )
    l.text = f"{{{tags}}}{obj.text}"

    io.write_line(l)


@io.track
def leadout_effect(line: Line, obj: Syllable | Char, l: Line):
    l.layer = 0
    l.start_time = line.start_time + obj.end_time
    l.end_time = line.end_time + line.leadout // 2

    tags = rf"\an5\pos({obj.center},{obj.middle})\fad(0,{line.leadout // 2})"
    l.text = f"{{{tags}}}{obj.text}"

    io.write_line(l)


@io.track
def romaji(line: Line, l: Line):
    for syl in Utils.all_non_empty(line.syls):
        leadin_effect(line, syl, l)
        main_effect(line, syl, l)
        leadout_effect(line, syl, l)


@io.track
def kanji(line: Line, l: Line):
    for char in Utils.all_non_empty(line.chars):
        leadin_effect(line, char, l)
        main_effect(line, char, l)
        leadout_effect(line, char, l)


@io.track
def sub(line: Line, l: Line):
    l.start_time = line.start_time - line.leadin // 2
    l.end_time = line.end_time + line.leadout // 2

    tags = rf"\fad({line.leadin // 2}, {line.leadout // 2})"
    l.text = f"{{{tags}}}{line.text}"

    io.write_line(l)


# Generating lines
for line in lines:
    if line.styleref.alignment >= 7:
        romaji(line, line.copy())
    elif line.styleref.alignment >= 4:
        kanji(line, line.copy())
    else:
        sub(line, line.copy())

io.save()
io.open_aegisub()
