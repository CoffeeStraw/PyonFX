"""
Tutorial: Adding shapes

This tutorial demonstrates how to make use of the Shape class to enrich KFXes.

The script creates two main effect types:
• `heartbeat_effect`: Continuous pulsing hearts on left and right sides of the screen
• `highlight_effect_shapes`: Random shapes that move and rotate behind each syllable during singing

Exercise:
• Try creating a pattern of equally spaced semi-transparent shapes behind the line instead of the 2 hearts
• Try changing the shape's alignment for the highlight effect or add a \\org tag to change the result of the \\frz tag
• Try extending these effects also to kanji and translation lines
"""

import random

from pyonfx import Ass, Convert, Line, Shape, Syllable, Utils

io = Ass("../../ass/romaji_kanji_translation.ass")
meta, styles, lines = io.get_data()


def generate_oscillating_transforms(
    start_time: int, end_time: int, cycle_duration: int, tags1: str, tags2: str
) -> str:
    """Generate a string of oscillating \\t transformations between two sets of tags.

    Alternates tags1/tags2 every half of cycle_duration, from start_time to end_time.
    """
    duration = end_time - start_time
    if duration <= 0 or cycle_duration <= 0:
        return ""

    half_cycle = cycle_duration // 2
    transforms = []

    # We step through each full cycle
    for current_time in range(0, duration, cycle_duration):
        first_half_end = min(current_time + half_cycle, duration)
        second_half_end = min(current_time + cycle_duration, duration)

        # First half: to tags1
        if first_half_end > current_time:
            transforms.append(
                f"\\t({start_time + current_time},{start_time + first_half_end},{tags1})"
            )
        # Second half: to tags2
        if second_half_end > first_half_end:
            transforms.append(
                f"\\t({start_time + first_half_end},{start_time + second_half_end},{tags2})"
            )

    return "".join(transforms)


@io.track
def heartbeat_effect(line: Line, l: Line):
    """Creates pulsing hearts on the left and right sides of each line"""
    l.layer = 0
    l.start_time = line.start_time - line.leadin // 2
    l.end_time = line.end_time + line.leadout // 2

    # Configuration
    HEART_SHAPE = Shape.heart(30)
    HEARTBEAT_PERIOD = 800  # milliseconds for one heartbeat cycle
    HEART_SCALE_MIN = 80  # minimum scale percentage
    HEART_SCALE_MAX = 120  # maximum scale percentage
    HEART_OFFSET = 30  # pixels spacing from text

    # Generate oscillating scale transforms
    scale_max = rf"\fscx{HEART_SCALE_MAX}\fscy{HEART_SCALE_MAX}"
    scale_min = rf"\fscx{HEART_SCALE_MIN}\fscy{HEART_SCALE_MIN}"
    oscillating_transforms = generate_oscillating_transforms(
        0, l.duration, HEARTBEAT_PERIOD, scale_max, scale_min
    )

    # Prepare common tags for both hearts
    common_tags = (
        rf"\fad({line.leadin // 4},{line.leadin // 4})"
        rf"{oscillating_transforms}"
        rf"\1c&HEAE3FF&\3c&HCBBBFF&\bord2\shad0\p1"
    )

    # Left heart
    position_tags = rf"\an5\pos({line.left - HEART_OFFSET},{line.middle})"
    l.text = f"{{{position_tags}{common_tags}}}{HEART_SHAPE}"
    io.write_line(l)

    # Right heart
    position_tags = rf"\an5\pos({line.right + HEART_OFFSET},{line.middle})"
    l.text = f"{{{position_tags}{common_tags}}}{HEART_SHAPE}"
    io.write_line(l)


@io.track
def highlight_effect_shapes(line: Line, syl: Syllable, l: Line):
    """Creates random moving and rotating shapes behind syllables"""
    l.layer = 0
    l.start_time = line.start_time + syl.start_time
    l.end_time = line.start_time + syl.end_time

    # Configuration
    SHAPE_SIZE = 20  # pixels
    HIGHLIGHT_SHAPES: list[Shape] = [
        Shape.triangle(SHAPE_SIZE, SHAPE_SIZE),
        Shape.rectangle(SHAPE_SIZE, SHAPE_SIZE),
        Shape.polygon(5, SHAPE_SIZE),  # pentagon
        Shape.polygon(6, SHAPE_SIZE),  # hexagon
        Shape.ellipse(SHAPE_SIZE, SHAPE_SIZE),
        Shape.circle(SHAPE_SIZE),
        Shape.ring(SHAPE_SIZE, SHAPE_SIZE // 2),
        Shape.star(5, SHAPE_SIZE // 2, SHAPE_SIZE),
        Shape.glance(4, SHAPE_SIZE // 2, SHAPE_SIZE),
    ]
    SHAPES_NUMBER = 10

    for _ in range(SHAPES_NUMBER):
        # Generate random shape
        shape = random.choice(HIGHLIGHT_SHAPES)

        # Random movement parameters
        start_x = syl.center
        start_y = syl.middle
        end_x = start_x + random.randint(-int(syl.width * 0.7), int(syl.width * 0.7))
        end_y = start_y + random.randint(-int(syl.height * 0.7), int(syl.height * 0.7))

        # Random rotation
        rotation = random.randint(90, 270) * (1 if random.random() > 0.5 else -1)

        # Random color (bright colors)
        r = random.randint(127, 255)
        g = random.randint(127, 255)
        b = random.randint(127, 255)
        color = Convert.color_rgb_to_ass((r, g, b))

        # Fade out duration
        fade_duration = syl.duration // 4

        tags = (
            rf"\an5\move({start_x},{start_y},{end_x},{end_y})"
            rf"\fad({fade_duration},{fade_duration})"
            rf"\t(\frz{rotation})"
            rf"\fscx{syl.height}\fscy{syl.height}"
            rf"\bord1\1c{color}\3c&H000000&\p1"
        )
        l.text = f"{{{tags}}}{shape}"
        io.write_line(l)


@io.track
def leadin_effect(line: Line, syl: Syllable, l: Line):
    l.layer = 0
    l.start_time = line.start_time - line.leadin // 2
    l.end_time = line.start_time + syl.start_time

    tags = rf"\an5\pos({syl.center},{syl.middle})\fad({line.leadin // 2},0)"
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


@io.track
def romaji(line: Line, l: Line):
    heartbeat_effect(line, l)
    for syl in Utils.all_non_empty(line.syls):
        leadin_effect(line, syl, l)
        highlight_effect(line, syl, l)
        highlight_effect_shapes(line, syl, l)
        leadout_effect(line, syl, l)


# Process all lines
for line in Utils.all_non_empty(lines):
    l = line.copy()
    if line.styleref.alignment >= 7:
        romaji(line, l)

io.save()
io.open_aegisub()
