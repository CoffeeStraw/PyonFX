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

For the kanji function, you can just notice that it is a lazy CTRL+C and CTRL+V of the romaji function,
but using chars instead of syls. Try yourself what happens if you use syllables for kanji!
"""

from pyonfx import *

io = Ass("in.ass")
meta, styles, lines = io.get_data()


def romaji(line, l):
    for syl in Utils.all_non_empty(line.syls):
        # Leadin Effect
        l.layer = 0

        l.start_time = line.start_time - line.leadin / 2
        l.end_time = line.start_time + syl.start_time
        l.dur = l.end_time - l.start_time

        l.text = "{\\an5\\pos(%.3f,%.3f)\\fad(%d,0)}%s" % (
            syl.center,
            syl.middle,
            line.leadin / 2,
            syl.text,
        )

        io.write_line(l)

        # Main Effect
        l.layer = 1

        l.start_time = line.start_time + syl.start_time
        l.end_time = line.start_time + syl.end_time
        l.dur = l.end_time - l.start_time

        l.text = (
            "{\\an5\\pos(%.3f,%.3f)"
            "\\t(0,%d,0.5,\\1c&HFFFFFF&\\3c&HABABAB&\\fscx125\\fscy125)"
            "\\t(%d,%d,1.5,\\fscx100\\fscy100\\1c%s\\3c%s)}%s"
            % (
                syl.center,
                syl.middle,
                l.dur / 3,
                l.dur / 3,
                l.dur,
                line.styleref.color1,
                line.styleref.color3,
                syl.text,
            )
        )

        io.write_line(l)

        # Leadout Effect
        l.layer = 0

        l.start_time = line.start_time + syl.end_time
        l.end_time = line.end_time + line.leadout / 2
        l.dur = l.end_time - l.start_time

        l.text = "{\\an5\\pos(%.3f,%.3f)\\fad(0,%d)}%s" % (
            syl.center,
            syl.middle,
            line.leadout / 2,
            syl.text,
        )

        io.write_line(l)


def kanji(line, l):
    for char in Utils.all_non_empty(line.chars):
        # Leadin Effect
        l.layer = 0

        l.start_time = line.start_time - line.leadin / 2
        l.end_time = line.start_time + char.start_time
        l.dur = l.end_time - l.start_time

        l.text = "{\\an5\\pos(%.3f,%.3f)\\fad(%d,0)}%s" % (
            char.center,
            char.middle,
            line.leadin / 2,
            char.text,
        )

        io.write_line(l)

        # Main Effect
        l.layer = 1

        l.start_time = line.start_time + char.start_time
        l.end_time = line.start_time + char.end_time
        l.dur = l.end_time - l.start_time

        l.text = (
            "{\\an5\\pos(%.3f,%.3f)"
            "\\t(0,%d,0.5,\\1c&HFFFFFF&\\3c&HABABAB&\\fscx125\\fscy125)"
            "\\t(%d,%d,1.5,\\fscx100\\fscy100\\1c%s\\3c%s)}%s"
            % (
                char.center,
                char.middle,
                l.dur / 3,
                l.dur / 3,
                l.dur,
                line.styleref.color1,
                line.styleref.color3,
                char.text,
            )
        )

        io.write_line(l)

        # Leadout Effect
        l.layer = 0

        l.start_time = line.start_time + char.end_time
        l.end_time = line.end_time + line.leadout / 2
        l.dur = l.end_time - l.start_time

        l.text = "{\\an5\\pos(%.3f,%.3f)\\fad(0,%d)}%s" % (
            char.center,
            char.middle,
            line.leadout / 2,
            char.text,
        )

        io.write_line(l)


def sub(line, l):
    # Translation Effect
    l.start_time = line.start_time - line.leadin / 2
    l.end_time = line.end_time + line.leadout / 2
    l.dur = l.end_time - l.start_time

    l.text = "{\\fad(%d,%d)}%s" % (line.leadin / 2, line.leadout / 2, line.text)

    io.write_line(l)


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
