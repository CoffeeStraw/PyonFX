from pyonfx import *
import random

io = Ass("in.ass")
meta, styles, lines = io.get_data()

circle = Shape.ellipse(20, 20)


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

        FU = FrameUtility(
            line.start_time + syl.start_time, line.start_time + syl.end_time
        )
        rand = random.uniform(-10, 10)

        # Starting to iterate over the frames
        for s, e, i, n in FU:
            l.layer = 1

            l.start_time = s
            l.end_time = e

            fsc = 100
            fsc += FU.add(0, syl.duration / 3, 20)
            fsc += FU.add(syl.duration / 3, syl.duration, -20)

            alpha = 0
            alpha += FU.add(syl.duration / 2, syl.duration, 255)
            alpha = Convert.alpha_dec_to_ass(int(alpha))

            l.text = "{\\an9\\pos(%.3f,%.3f)\\fscx%.3f\\fscy%.3f}%s" % (
                syl.right,
                syl.top,
                fsc,
                fsc,
                syl.text,
            )

            io.write_line(l)

            l.text = (
                "{\\an5\\pos(%.3f,%.3f)\\fscx%.3f\\fscy%.3f\\1c&H0000FF&\\bord0\\shad0\\blur2\\alpha%s\\clip(%s)\\p1}%s"
                % (
                    syl.center + rand,
                    syl.middle + rand,
                    fsc,
                    fsc,
                    alpha,
                    Convert.text_to_clip(syl, an=9, fscx=fsc, fscy=fsc),
                    circle,
                )
            )

            io.write_line(l)

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


# Generating lines
for line in lines:
    if line.styleref.alignment >= 7:
        romaji(line, line.copy())

io.save()
io.open_aegisub()
