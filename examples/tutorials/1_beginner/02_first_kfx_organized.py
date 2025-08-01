"""
Tutorial: Creating your first organized Karaoke Effect

This tutorial recreates the KFX seen in '01_first_kfx.py', but using an organized structure and a few utilities.

We have refactored the code into three distinct functions:
• `leadin_effect`: makes the syllable fade in before being sung
• `main_effect`: highlights the syllable with scaling and color transitions
• `leadout_effect`: makes the syllable fade out after being sung

We also use:
• `Utils.all_non_empty()` to skip empty syllables and comment lines
• `io.track()` decorator to track statistics for each effect

Exercise:
• Try to change the leadin/leadout to make the syllable move from y=middle-80 to y=middle during the effect
• Try to change the growing duration of the main effect to make the syllable grow faster or slower
"""

from pyonfx import Ass, Line, Syllable, Utils

io = Ass("../../ass/romaji_kanji_translation.ass")
meta, styles, lines = io.get_data()


@io.track
def leadin_effect(line: Line, syl: Syllable, l: Line):
    l.layer = 0
    l.start_time = line.start_time - line.leadin // 2
    l.end_time = line.start_time + syl.start_time

    tags = rf"\an5\pos({syl.center},{syl.middle})\fad({line.leadin // 2},0)"
    l.text = f"{{{tags}}}{syl.text}"

    io.write_line(l)


@io.track
def main_effect(line: Line, syl: Syllable, l: Line):
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
        rf"\an5\pos({syl.center},{syl.middle})"
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

    tags = rf"\an5\pos({syl.center},{syl.middle})\fad(0,{line.leadout // 2})"
    l.text = f"{{{tags}}}{syl.text}"

    io.write_line(l)


# Generating lines
for line in Utils.all_non_empty(lines):
    if line.styleref.alignment >= 7:
        l = line.copy()
        for syl in Utils.all_non_empty(line.syls):
            leadin_effect(line, syl, l)
            main_effect(line, syl, l)
            leadout_effect(line, syl, l)

io.save()
io.open_aegisub()
