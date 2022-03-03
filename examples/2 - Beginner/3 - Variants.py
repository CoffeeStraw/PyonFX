"""
Inline effects is a method to define exclusive effects for syllables.
Fields "Actor" and "Effect" can also be used to define exclusive effects, but you will define them for the whole line.

In this example, romajis are looking for inline effects
"m1" and "m2" to choose a main effect to apply to syls' text.
Kanjis are looking for lines' field "Effect", to choose what kind of effect we want to apply.
In addition, for romaji there's a star jumping over syls by frame-per-frame positioning.

In this example we can also see in action another utility provided by PyonFX: ColorUtility.
It is used to extract color changes from some lines and interpolate them for each generated line without effort.
Colors will add a really nice touch to your KFXs, so it is important to have a comfy way to set up them and use them in your effects.
In the translation lines we will create some clipped text colorated as an example of the application.
You can also make some simpler usage, like just applying color changes to the whole line, which is what karaokers normally do.

It could look like much code for such a simple effect, but it's needed and an easy method with much potential for extensions.
"""

from pyonfx import *
import random
import math

io = Ass("in2.ass")
meta, styles, lines = io.get_data()

# Creating the star and extracting all the color changes from the input file
star = Shape.star(5, 4, 10)
CU = ColorUtility(lines)


def romaji(line, l):
    # Setting up a delay, we will use it as duration time of the leadin and leadout effects
    delay = 300
    # Setting up offset variables, we will use them for the \move in leadin and leadout effects
    off_x = 35
    off_y = 15

    # Leadin Effect
    for syl in Utils.all_non_empty(line.syls):
        l.layer = 0

        l.start_time = (
            line.start_time + 25 * syl.i - delay - 80
        )  # Remove 80 to start_time to let leadin finish a little bit earlier than the main effect of the first syllable
        l.end_time = line.start_time + syl.start_time
        l.dur = l.end_time - l.start_time

        l.text = (
            "{\\an5\\move(%.3f,%.3f,%.3f,%.3f,0,%d)\\blur2\\t(0,%d,\\blur0)\\fad(%d,0)}%s"
            % (
                syl.center + math.cos(syl.i / 2) * off_x,
                syl.middle + math.sin(syl.i / 4) * off_y,
                syl.center,
                syl.middle,
                delay,
                delay,
                delay,
                syl.text,
            )
        )

        io.write_line(l)

    # Main Effect
    for syl in Utils.all_non_empty(line.syls):
        l.layer = 1

        l.start_time = line.start_time + syl.start_time
        l.end_time = line.start_time + syl.end_time + 100
        l.dur = l.end_time - l.start_time

        c1 = "&H81F4FF&"
        c3 = "&H199AAA&"
        # Change color if inline_fx is m1
        if syl.inline_fx == "m1":
            c1 = "&H8282FF&"
            c3 = "&H191AAA&"

        on_inline_effect_2 = ""
        # Apply rotation if inline_fx is m2
        if syl.inline_fx == "m2":
            on_inline_effect_2 = "\\t(0,%d,\\frz%.3f)\\t(%d,%d,\\frz0)" % (
                l.dur / 4,
                random.uniform(-40, 40),
                l.dur / 4,
                l.dur,
            )

        l.text = (
            "{\\an5\\pos(%.3f,%.3f)%s\\t(0,80,\\fscx105\\fscy105\\1c%s\\3c%s)\\t(80,%d,\\fscx100\\fscy100\\1c%s\\3c%s)}%s"
            % (
                syl.center,
                syl.middle,
                on_inline_effect_2,
                c1,
                c3,
                l.dur - 80,
                line.styleref.color1,
                line.styleref.color3,
                syl.text,
            )
        )

        io.write_line(l)

        # Animating star shape that jumps over the syllables
        # Jump-in to the first syl
        jump_height = 18
        if syl.i == 0:
            FU = FrameUtility(line.start_time - line.leadin / 2, line.start_time)
            for s, e, i, n in FU:
                l.start_time = s
                l.end_time = e
                frame_pct = i / n

                x = syl.center - syl.width * (1 - frame_pct)
                y = syl.top - math.sin(frame_pct * math.pi) * jump_height

                alpha = 255
                alpha += FU.add(0, syl.duration, -255)
                alpha = Convert.alpha_dec_to_ass(int(alpha))

                l.text = (
                    "{\\alpha%s\\pos(%.3f,%.3f)\\bord1\\blur1\\1c%s\\3c%s\\p1}%s"
                    % (alpha, x, y, c1, c3, star)
                )
                io.write_line(l)

        # Jump to the next syl or to the end of line
        jump_width = (
            line.syls[syl.i + 1].center - syl.center
            if syl.i != len(line.syls) - 1
            else syl.width
        )
        FU = FrameUtility(
            line.start_time + syl.start_time, line.start_time + syl.end_time
        )
        for s, e, i, n in FU:
            l.start_time = s
            l.end_time = e
            frame_pct = i / n

            x = syl.center + frame_pct * jump_width
            y = syl.top - math.sin(frame_pct * math.pi) * jump_height

            alpha = 0
            # Last jump should fade-out
            if syl.i == len(line.syls) - 1:
                alpha += FU.add(0, syl.duration, 255)
            alpha = Convert.alpha_dec_to_ass(int(alpha))

            l.text = "{\\alpha%s\\pos(%.3f,%.3f)\\bord1\\blur1\\1c%s\\3c%s\\p1}%s" % (
                alpha,
                x,
                y,
                c1,
                c3,
                star,
            )
            io.write_line(l)

    # Leadout Effect
    for syl in Utils.all_non_empty(line.syls):
        l.layer = 0

        l.start_time = line.start_time + syl.end_time + 100
        l.end_time = line.end_time - 25 * (len(line.syls) - syl.i) + delay + 100
        l.dur = l.end_time - l.start_time

        l.text = (
            "{\\an5\\move(%.3f,%.3f,%.3f,%.3f,%d,%d)\\t(%d,%d,\\blur2)\\fad(0,%d)}%s"
            % (
                syl.center,
                syl.middle,
                syl.center + math.cos(syl.i / 2) * off_x,
                syl.middle + math.sin(syl.i / 4) * off_y,
                l.dur - delay,
                l.dur,
                l.dur - delay,
                l.dur,
                delay,
                syl.text,
            )
        )

        io.write_line(l)


def kanji(line, l):
    # Setting up a delay, we will use it as duration time of the leadin and leadout effects
    delay = 300
    # Setting up offset variables, we will use them for the \move in leadin and leadout effects
    off_x = 35
    off_y = 15

    # Leadin Effect
    for syl in Utils.all_non_empty(line.syls):
        l.layer = 0

        l.start_time = (
            line.start_time + 25 * syl.i - delay - 80
        )  # Remove 80 to start_time to let leadin finish a little bit earlier than the main effect of the first syllable
        l.end_time = line.start_time + syl.start_time
        l.dur = l.end_time - l.start_time

        l.text = (
            "{\\an5\\move(%.3f,%.3f,%.3f,%.3f,0,%d)\\blur2\\t(0,%d,\\blur0)\\fad(%d,0)}%s"
            % (
                syl.center + math.cos(syl.i / 2) * off_x,
                syl.middle + math.sin(syl.i / 4) * off_y,
                syl.center,
                syl.middle,
                delay,
                delay,
                delay,
                syl.text,
            )
        )

        io.write_line(l)

    # Main Effect
    for syl in Utils.all_non_empty(line.syls):
        l.layer = 1

        l.start_time = line.start_time + syl.start_time
        l.end_time = line.start_time + syl.end_time + 100
        l.dur = l.end_time - l.start_time

        c1 = "&H81F4FF&"
        c3 = "&H199AAA&"
        # Change color if effect field is m1
        if line.effect == "m1":
            c1 = "&H8282FF&"
            c3 = "&H191AAA&"

        on_inline_effect_2 = ""
        # Apply rotation if effect field is m2
        if line.effect == "m2":
            on_inline_effect_2 = "\\t(0,%d,\\frz%.3f)\\t(%d,%d,\\frz0)" % (
                l.dur / 4,
                random.uniform(-40, 40),
                l.dur / 4,
                l.dur,
            )

        l.text = (
            "{\\an5\\pos(%.3f,%.3f)%s\\t(0,80,\\fscx105\\fscy105\\1c%s\\3c%s)\\t(80,%d,\\fscx100\\fscy100\\1c%s\\3c%s)}%s"
            % (
                syl.center,
                syl.middle,
                on_inline_effect_2,
                c1,
                c3,
                l.dur - 80,
                line.styleref.color1,
                line.styleref.color3,
                syl.text,
            )
        )

        io.write_line(l)

    # Leadout Effect
    for syl in Utils.all_non_empty(line.syls):
        l.layer = 0

        l.start_time = line.start_time + syl.end_time + 100
        l.end_time = line.end_time - 25 * (len(line.syls) - syl.i) + delay + 100
        l.dur = l.end_time - l.start_time

        l.text = (
            "{\\an5\\move(%.3f,%.3f,%.3f,%.3f,%d,%d)\\t(%d,%d,\\blur2)\\fad(0,%d)}%s"
            % (
                syl.center,
                syl.middle,
                syl.center + math.cos(syl.i / 2) * off_x,
                syl.middle + math.sin(syl.i / 4) * off_y,
                l.dur - delay,
                l.dur,
                l.dur - delay,
                l.dur,
                delay,
                syl.text,
            )
        )

        io.write_line(l)


def sub(line, l):
    # Translation Effect
    l.layer = 0

    l.start_time = line.start_time - line.leadin / 2
    l.end_time = line.end_time + line.leadout / 2
    l.dur = l.end_time - l.start_time

    # Getting interpolated color changes (notice that we do that only after having set up all the times, that's important)
    colors = CU.get_color_change(l)

    # Base text
    l.text = "{\\an5\\pos(%.3f,%.3f)\\fad(%d,%d)}%s" % (
        line.center,
        line.middle,
        line.leadin / 2,
        line.leadout / 2,
        line.text,
    )
    io.write_line(l)

    # Random clipped text colorated
    l.layer = 1
    for i in range(1, int(line.width / 80)):
        x_clip = line.left + random.uniform(0, line.width)
        y_clip = line.top - 5

        clip = (
            x_clip,
            y_clip,
            x_clip + random.uniform(10, 30),
            y_clip + line.height + 10,
        )

        l.text = "{\\an5\\pos(%.3f,%.3f)\\fad(%d,%d)\\clip(%d,%d,%d,%d)%s}%s" % (
            line.center,
            line.middle,
            line.leadin / 2,
            line.leadout / 2,
            clip[0],
            clip[1],
            clip[2],
            clip[3],
            colors,
            line.text,
        )
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
