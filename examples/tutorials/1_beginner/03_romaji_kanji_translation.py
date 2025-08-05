"""
Tutorial: Creating a Karaoke Effect for Romaji, Kanji and Translation lines

This tutorial extend the KFX seen in '02_first_kfx_organized.py' by adding an effect for kanji and translation lines.

We pass the `vertical_kanji` flag to the Ass constructor to make the kanji lines vertical.

As before, there are three distinct effect functions:
• `leadin_effect`: makes the syllable fade in before being sung
• `highlight_effect`: highlights the syllable with scaling and color transitions
• `leadout_effect`: makes the syllable fade out after being sung

It also distinguishes between subtitle types:
• The `romaji` function processes syllables for lines with alignment 7 or higher (Romaji)
• The `kanji` function processes individual characters for lines with intermediate alignment
• The `translation` function handles other subtitle lines with lower alignment

We re-use the same effect functions for romaji and kanji.

Exercise:
• Try making a different effect for the kanji instead of re-using the same effect functions.
"""

from pyonfx import Ass, Line, Syllable, Utils

io = Ass("../../ass/romaji_kanji_translation.ass", vertical_kanji=True)
meta, styles, lines = io.get_data()


@io.track
def leadin_effect(line: Line, syl: Syllable, l: Line):
    l.layer = 0
    l.start_time = line.start_time - line.leadin // 2
    l.end_time = line.start_time + syl.start_time

    tags = rf"\an5\pos({syl.center:.3f},{syl.middle:.3f})\fad({line.leadin // 2},0)"
    l.text = f"{{{tags}}}{syl.text}"

    io.write_line(l)


@io.track
def highlight_effect(line: Line, syl: Syllable, l: Line):
    l.layer = 1
    l.start_time = line.start_time + syl.start_time
    l.end_time = line.start_time + syl.end_time

    # Original style values
    c1 = line.styleref.color1
    c3 = line.styleref.color3
    fscx = line.styleref.scale_x
    fscy = line.styleref.scale_y

    # Target values
    t_c1 = "&HFFFFFF&"
    t_c3 = "&HABABAB&"
    t_fscx = fscx * 1.25
    t_fscy = fscy * 1.25
    grow_duration = syl.duration // 2

    tags = (
        rf"\an5\pos({syl.center:.3f},{syl.middle:.3f})"
        rf"\t(0,{grow_duration},\fscx{t_fscx}\fscy{t_fscy}\1c{t_c1}\3c{t_c3})"
        rf"\t({grow_duration},{syl.duration},\fscx{fscx}\fscy{fscy}\1c{c1}\3c{c3})"
    )
    l.text = f"{{{tags}}}{syl.text}"

    io.write_line(l)


@io.track
def leadout_effect(line: Line, syl: Syllable, l: Line):
    l.layer = 0
    l.start_time = line.start_time + syl.end_time
    l.end_time = line.end_time + line.leadout // 2

    tags = rf"\an5\pos({syl.center:.3f},{syl.middle:.3f})\fad(0,{line.leadout // 2})"
    l.text = f"{{{tags}}}{syl.text}"

    io.write_line(l)


@io.track
def romaji(line: Line, l: Line):
    for syl in Utils.all_non_empty(line.syls):
        leadin_effect(line, syl, l)
        highlight_effect(line, syl, l)
        leadout_effect(line, syl, l)


@io.track
def kanji(line: Line, l: Line):
    for syl in Utils.all_non_empty(line.syls):
        leadin_effect(line, syl, l)
        highlight_effect(line, syl, l)
        leadout_effect(line, syl, l)


@io.track
def translation(line: Line, l: Line):
    l.start_time = line.start_time - line.leadin // 2
    l.end_time = line.end_time + line.leadout // 2

    tags = rf"\fad({line.leadin // 2}, {line.leadout // 2})"
    l.text = f"{{{tags}}}{line.text}"

    io.write_line(l)


# Generating lines
for line in Utils.all_non_empty(lines):
    l = line.copy()
    if line.styleref.alignment >= 7:
        romaji(line, l)
    elif line.styleref.alignment >= 4:
        kanji(line, l)
    else:
        translation(line, l)

io.save()
io.open_aegisub()
