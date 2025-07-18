"""
Morphing Example. To be refined before considering it complete.
"""

import random

from pyonfx import *

# Setup I/O
io = Ass("in.ass")
meta, styles, lines = io.get_data()

# A set of shapes we can randomly choose from
AVAILABLE_SHAPES = [
    Shape.ellipse(25, 25),  # Circle
    Shape.polygon(4, 25),  # Square
    Shape.polygon(3, 25),  # Triangle
    Shape.star(5, 10, 20),  # 5-point star
    Shape.star(6, 10, 20),  # 6-point star
    Shape.heart(28),  # Heart
    Shape.ring(17, 8),  # Ring
]

# Simple colour palette (cycling through)
PALETTE = [
    "&H0066FF&",
    "&HFF6600&",
    "&H00CC66&",
    "&HFF0066&",
    "&H6600FF&",
    "&HFFFF00&",
    "&H00FFFF&",
]


def romaji(line: Line, l: Line) -> None:
    """Create per-syllable lead-in: bouncing random shape → morph into text."""

    # Lead-in timing configuration (in ms)
    LEADIN_TOTAL = 1000  # Total lead-in duration per syllable before syl.start_time
    BOUNCE_PART = 0.6  # 60 % of lead-in spent on falling + bounce
    BOUNCE_HEIGHT = 80  # Pixels the shape drops from above the baseline

    # Lead-out timing configuration (in ms)
    LEADOUT_TOTAL = 800  # Total lead-out duration per syllable after syl.end_time
    LEADOUT_DROP = 50  # Pixels to drop down during leadout
    LEADOUT_ROTATION = -180  # Degrees to rotate during leadout (negative = left)

    for syl in Utils.all_non_empty(line.syls):
        # Choose random appearance
        random_shape = random.choice(AVAILABLE_SHAPES)
        colour = PALETTE[syl.i % len(PALETTE)]
        frz_start = random.randint(-50, 50)

        # Cache text shape
        text_shape = Convert.text_to_shape(syl)

        # Compute time segments
        # We slightly stagger syllables so they don't start simultaneously
        leadin_start = line.start_time + 100 * syl.i - LEADIN_TOTAL
        bounce_end = leadin_start + int(LEADIN_TOTAL * BOUNCE_PART)
        bounce_duration = bounce_end - leadin_start
        morph_end = leadin_start + LEADIN_TOTAL  # This equals syl absolute start

        # 1) Falling + bounce stage (random shape)
        FU_bounce = FrameUtility(leadin_start, bounce_end, io.input_timestamps)
        for s, e, i, n in FU_bounce:
            l.layer = 0
            l.start_time = s
            l.end_time = e

            t = i / n  # 0 → 1 progress through bounce stage

            # Position – simple two-phase drop and bounce
            x = syl.left
            y = syl.top - BOUNCE_HEIGHT
            y += FU_bounce.add(0, bounce_duration * 0.85, BOUNCE_HEIGHT + 20)
            y -= FU_bounce.add(bounce_duration * 0.85, bounce_duration, 20)

            # Rotate the shape
            curr_frz = frz_start
            curr_frz -= FU_bounce.add(0, bounce_duration * 0.85, frz_start)

            l.text = (
                "{\\an7\\pos(%.3f,%.3f)\\p1\\1c%s\\bord2\\3c&H000000&\\frz%s}%s"
                % (x, y, colour, curr_frz, random_shape)
            )
            io.write_line(l)

        # 2) Morph stage – shape morphs to text
        if morph_end > bounce_end:
            FU_morph = FrameUtility(
                int(bounce_end), int(morph_end), io.input_timestamps
            )
            for s, e, i, n in FU_morph:
                l.layer = 0
                l.start_time = s
                l.end_time = e

                t = i / n  # 0 → 1 progress through morph
                morphed_shape = random_shape.morph(text_shape, t)

                # Gradually change color to the original text color
                curr_colour = Utils.interpolate(t, colour, line.styleref.color1)

                l.text = "{\\an7\\pos(%.3f,%.3f)\\p1\\1c%s\\bord2\\3c&H000000&}%s" % (
                    syl.left,
                    syl.top,
                    curr_colour,
                    morphed_shape,
                )
                io.write_line(l)

        # Static syl waiting for beginning of main effect
        l.layer = 0
        l.start_time = l.end_time  # Last line end time
        l.end_time = line.start_time + syl.start_time
        l.text = "{\\an5\\pos(%.3f,%.3f)}%s" % (syl.center, syl.middle, syl.text)
        io.write_line(l)

        # Main Effect
        l.layer = 1

        l.start_time = line.start_time + syl.start_time
        l.end_time = line.end_time + 100 * syl.i
        l.duration = l.end_time - l.start_time

        l.text = (
            "{\\an5\\pos(%.3f,%.3f)"
            "\\t(0,%d,0.5,\\1c&HFFFFFF&\\3c&HABABAB&\\fscx125\\fscy125)"
            "\\t(%d,%d,1.5,\\fscx100\\fscy100\\1c%s\\3c%s)}%s"
            % (
                syl.center,
                syl.middle,
                syl.duration / 3,
                syl.duration / 3,
                syl.duration,
                line.styleref.color1,
                line.styleref.color3,
                syl.text,
            )
        )
        io.write_line(l)

        # 4) Leadout Effect - text morphs back to shape, moves down, rotates and fades
        leadout_start = line.end_time + 100 * syl.i
        leadout_end = leadout_start + LEADOUT_TOTAL

        # Split leadout into morph phase and movement/fade phase
        morph_back_duration = int(LEADOUT_TOTAL * 0.4)  # 40% for morphing back
        movement_duration = LEADOUT_TOTAL - morph_back_duration  # 60% for movement/fade

        morph_back_end = leadout_start + morph_back_duration

        # Phase 1: Text morphs back to shape while changing color
        FU_morph_back = FrameUtility(
            int(leadout_start), int(morph_back_end), io.input_timestamps
        )
        for s, e, i, n in FU_morph_back:
            l.layer = 2
            l.start_time = s
            l.end_time = e

            t = i / n  # 0 → 1 progress through morph back
            morphed_shape = text_shape.morph(random_shape, t)

            # Change color from text color back to shape color
            curr_colour = Utils.interpolate(t, line.styleref.color1, colour)

            l.text = "{\\an7\\pos(%.3f,%.3f)\\p1\\1c%s\\bord2\\3c&H000000&}%s" % (
                syl.left,
                syl.top,
                curr_colour,
                morphed_shape,
            )
            io.write_line(l)

        # Phase 2: Shape moves down, rotates left and fades out
        if leadout_end > morph_back_end:
            FU_leadout = FrameUtility(
                int(morph_back_end), int(leadout_end), io.input_timestamps
            )
            for s, e, i, n in FU_leadout:
                l.layer = 2
                l.start_time = s
                l.end_time = e

                t = i / n  # 0 → 1 progress through movement/fade

                # Position - move down gradually
                x = syl.left
                y = syl.top + FU_leadout.add(0, movement_duration, LEADOUT_DROP)

                # Rotation - rotate to the left
                rotation = FU_leadout.add(0, movement_duration, LEADOUT_ROTATION)

                # Fade out
                alpha_dec = int(FU_leadout.add(0, movement_duration, 255))
                alpha_ass = Convert.alpha_dec_to_ass(alpha_dec)

                l.text = (
                    "{\\alpha%s\\an7\\pos(%.3f,%.3f)\\frz%.1f\\p1\\1c%s\\bord2\\3c&H000000&}%s"
                    % (alpha_ass, x, y, rotation, colour, random_shape)
                )
                io.write_line(l)


# Subtitle effect - leadin/leadout morphing between lines
def sub(line: Line, l: Line, prev_line=None, next_line=None) -> None:
    """Create subtitle effect with text morphing leadout to next line."""

    # Base line
    l.layer = 0
    l.start_time = line.start_time - (int(line.leadin) if prev_line is None else 0)
    l.end_time = line.end_time + (int(line.leadout) if next_line is None else 0)
    l.text = "{\\an5\\pos(%.3f,%.3f)\\fad(%d,%d)}%s" % (
        line.center,
        line.middle,
        int(line.leadin) if prev_line is None else 0,
        int(line.leadout) if next_line is None else 0,
        line.text,
    )
    io.write_line(l)

    if next_line is not None:
        # Convert line text to shape for morphing
        line_text_shape = Convert.text_to_shape(line)

        l.layer = 0
        l.start_time = line.end_time
        l.end_time = next_line.start_time

        # Get next line's text as shape
        next_text_shape = Convert.text_to_shape(next_line)
        line_text_shape.move(line.left, line.top)
        next_text_shape.move(next_line.left, next_line.top)
        # print(line.left, next_line.left)

        FU_leadout = FrameUtility(l.start_time, l.end_time, io.input_timestamps)

        for s, e, i, n in FU_leadout:
            l.start_time = s
            l.end_time = e

            t = i / n

            # Morph from current line text shape to next line text shape
            morphed_shape = line_text_shape.morph(next_text_shape, t)
            morphed_shape.move(-line.left, -line.top)

            l.text = "{\\an7\\pos(%.3f,%.3f)\\p1}%s" % (
                line.left,
                line.top,
                morphed_shape,
            )

            io.write_line(l)


# Separate romaji and subtitle lines for context-aware processing
romaji_lines = [
    line for line in Utils.all_non_empty(lines) if line.styleref.alignment >= 7
]
sub_lines = [
    line for line in Utils.all_non_empty(lines) if line.styleref.alignment <= 3
]

# Process romaji lines
for line in romaji_lines:
    romaji(line, line.copy())

# Process subtitle lines with previous/next line context
for i, line in enumerate(sub_lines):
    prev_line = sub_lines[i - 1] if i > 0 else None
    next_line = sub_lines[i + 1] if i < len(sub_lines) - 1 else None
    sub(line, line.copy(), prev_line, next_line)

# Save and open in Aegisub for preview
io.save()
io.open_aegisub()
