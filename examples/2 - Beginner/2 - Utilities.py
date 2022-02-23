"""
The transform ASS tag makes some nice animations possible, but that shouldn't be enough for us!
The alternative is to create one dialog line for every frame. But frame per frame animation can be
pretty stressful to set up, and here's where an utility provided by pyonfx come handy.
In romaji, syllables jitter by frame-per-frame reposition is calculated and
fscx/fscy increase is calculated using FrameUtility, provided in the utils module.
    (Docs: https://pyonfx.readthedocs.io/en/latest/reference/utils.html#pyonfx.utils.FrameUtility)
    (About the random uniform function: https://docs.python.org/3/library/random.html#random.uniform)
You will also see a pretty standard way to make a gradual leadin and leadout, the main idea is to
leave some little delay between syllables so that there is more time to develop an effect.

For subtitles, we create a vertical static gradient.
As exercise, you can try to transform it into an horizontal one :)
"""

from pyonfx import *
import random

io = Ass("in.ass")
meta, styles, lines = io.get_data()


def romaji(line, l):
    for syl in Utils.all_non_empty(line.syls):
        # Setting up a delay, which will be my time for the leadin and leadout effect
        delay = 200

        # Leadin Effect
        l.layer = 0

        l.start_time = line.start_time + 25 * syl.i - delay
        l.end_time = line.start_time + syl.start_time
        l.dur = l.end_time - l.start_time

        l.text = "{\\an5\\pos(%.3f,%.3f)\\fad(%d,0)}%s" % (
            syl.center,
            syl.middle,
            delay,
            syl.text,
        )

        io.write_line(l)

        # Main Effect
        # Let's create a FrameUtility object and set up a radius for the random positions
        FU = FrameUtility(
            line.start_time + syl.start_time, line.start_time + syl.end_time
        )
        radius = 2

        # Starting to iterate over the frames
        for s, e, _, _ in FU:
            l.layer = 1

            l.start_time = s
            l.end_time = e

            # These lines of codes will reproduce
            # "\\t(0,%d,\\fscx140\\fscy140)\\t(%d,%d,\\fscx100\\fscy100)" % (syl.duration/3, syl.duration/3, syl.duration)
            fsc = 100
            fsc += FU.add(0, syl.duration / 3, 40)
            fsc += FU.add(syl.duration / 3, syl.duration, -40)

            l.text = "{\\an5\\pos(%.3f,%.3f)\\fscx%.3f\\fscy%.3f}%s" % (
                syl.center + random.uniform(-radius, radius),
                syl.middle + random.uniform(-radius, radius),
                fsc,
                fsc,
                syl.text,
            )

            io.write_line(l)

        # Leadout Effect
        l.layer = 0

        l.start_time = line.start_time + syl.end_time
        l.end_time = line.end_time - 25 * (len(line.syls) - syl.i) + delay
        l.dur = l.end_time - l.start_time

        l.text = "{\\an5\\pos(%.3f,%.3f)\\fad(0,%d)}%s" % (
            syl.center,
            syl.middle,
            delay,
            syl.text,
        )

        io.write_line(l)


def sub(line, l):
    # Translation Effect
    l.start_time = line.start_time - line.leadin / 2
    l.end_time = line.end_time + line.leadout / 2
    l.dur = l.end_time - l.start_time

    # Writing border
    l.text = "{\\an5\\pos(%.3f,%.3f)\\fad(%d,%d)}%s" % (
        line.center,
        line.middle,
        line.leadin / 2,
        line.leadout / 2,
        line.text,
    )

    io.write_line(l)

    # We define precision, increasing it will result in a gain on preformance and decrease of fidelity (due to less lines produced)
    precision = 1
    n = int(line.height / precision)

    for i in range(n):
        clip = "%d, %d, %d, %d" % (
            line.left,
            line.top + (line.height) * (i / n),
            line.right,
            line.top + (line.height) * ((i + 1) / n),
        )

        color = Utils.interpolate(i / n, "&H00FFF7&", "&H0000FF&", 1.4)

        l.text = "{\\an5\\pos(%.3f,%.3f)\\fad(%d,%d)\\clip(%s)\\bord0\\1c%s}%s" % (
            line.center,
            line.middle,
            line.leadin / 2,
            line.leadout / 2,
            clip,
            color,
            line.text,
        )

        io.write_line(l)


for line in lines:
    # Generating lines
    if line.styleref.alignment >= 7:
        romaji(line, line.copy())
    elif line.styleref.alignment <= 3:
        sub(line, line.copy())

io.save()
io.open_aegisub()
