"""
Tutorial: Adding variety

This tutorial demonstrates how to add variety to your effects by using:
• line.actor to personalize the effect for specific lines
• syl.inline_fx to apply special effects to specific syllables
• ColorUtility to change colors based on existing color transformations in the input file

Exercise:
• Try using line.effect instead of line.actor
• Try adding a "rotate" highlight effect, transforming over the \\frz tag: you'll find that the input .ass file already has some syllables marked with it
"""

from pyonfx import Ass, ColorUtility, Convert, Line, Syllable, Utils

io = Ass("../../ass/romaji_kanji_translation.ass", vertical_kanji=True)
meta, styles, lines = io.get_data()

# Set up ColorUtility to preserve existing color transformations
cu = ColorUtility(lines)

# Define color themes for different actors
ACTOR_THEMES = {
    "Singer1": {
        "highlight": "&H4B19E6&",  # Purple
        "outline": "&H8B4B9B&",  # Light purple
        "fade": "&HBB6BFF&",  # Very light purple
    },
    "Singer2": {
        "highlight": "&H19E64B&",  # Green
        "outline": "&H4B9B8B&",  # Light green
        "fade": "&H6BFFBB&",  # Very light green
    },
    "": {  # Default (no actor)
        "highlight": "&HFFFFFF&",  # White
        "outline": "&HABABAB&",  # Gray
        "fade": "&HDDDDDD&",  # Light gray
    },
}


@io.track
def leadin_effect(line: Line, syl: Syllable, l: Line):
    l.layer = 0
    l.start_time = line.start_time - line.leadin // 2
    l.end_time = line.start_time + syl.start_time

    # Original values
    original_c1 = line.styleref.color1
    original_c3 = line.styleref.color3

    # Configuration
    theme = ACTOR_THEMES.get(line.actor, ACTOR_THEMES[""])

    tags = (
        rf"\an5\pos({syl.center},{syl.middle})"
        rf"\1c{theme['fade']}\3c{theme['outline']}"
        rf"\t(0,{line.leadin // 2},\1c{original_c1}\3c{original_c3})"
        rf"\fad({line.leadin // 2},0)"
    )
    l.text = f"{{{tags}}}{syl.text}"

    io.write_line(l)


@io.track
def main_effect(line: Line, syl: Syllable, l: Line):
    l.layer = 1
    l.start_time = line.start_time + syl.start_time
    l.end_time = line.start_time + syl.end_time

    # Original values
    c1 = line.styleref.color1
    c3 = line.styleref.color3
    fscx = line.styleref.scale_x
    fscy = line.styleref.scale_y

    # Configuration
    theme = ACTOR_THEMES.get(line.actor, ACTOR_THEMES[""])
    new_fscx = fscx * 1.25
    new_fscy = fscy * 1.25

    tags = (
        rf"\an5\pos({syl.center},{syl.middle})"
        rf"\t(0,{syl.duration // 2},\fscx{new_fscx}\fscy{new_fscy}\1c{theme['highlight']}\3c{theme['outline']})"
        rf"\t({syl.duration // 2},{syl.duration},\fscx{fscx}\fscy{fscy}\1c{c1}\3c{c3})"
    )
    l.text = f"{{{tags}}}{syl.text}"

    io.write_line(l)


@io.track
def main_echo_effect(line: Line, syl: Syllable, l: Line):
    l.layer = 1
    l.start_time = line.start_time + syl.start_time
    l.end_time = line.start_time + syl.end_time

    # Get original color values
    c1 = line.styleref.color1
    fscx = line.styleref.scale_x
    fscy = line.styleref.scale_y

    # Configuration
    theme = ACTOR_THEMES.get(line.actor, ACTOR_THEMES[""])
    n_echo_layers = 8
    target_fscx = fscx * 1.6
    target_fscy = fscy * 1.6
    base_alpha = 130
    target_alpha = 230

    # Base layer
    tags = (
        rf"\an5\pos({syl.center},{syl.middle})"
        rf"\alpha&H00&"
        rf"\t(0,{syl.duration // 2},\1c{theme['highlight']})"
        rf"\t({syl.duration // 2},{syl.duration},\1c{c1})"
    )
    l.text = f"{{{tags}}}{syl.text}"
    io.write_line(l)

    # Echo layers
    for i in range(1, n_echo_layers + 1):
        l.layer = 1 + i

        # Target scale increases with each layer
        current_fscx = fscx + (target_fscx - fscx) * (i / n_echo_layers)
        current_fscy = fscy + (target_fscy - fscy) * (i / n_echo_layers)
        # Alpha decreases with each layer (from base_alpha to target_alpha)
        current_alpha = Convert.alpha_dec_to_ass(
            base_alpha + (target_alpha - base_alpha) * (i / n_echo_layers)
        )

        tags = (
            rf"\an5\pos({syl.center},{syl.middle})"
            rf"\alpha{current_alpha}"
            rf"\t(0,{syl.duration // 2},\1c{theme['highlight']}\fscx{current_fscx}\fscy{current_fscy})"
            rf"\t({syl.duration // 2},{syl.duration},\1c{c1}\fscx{fscx}\fscy{fscy})"
            rf"\fad({syl.duration // 4},{syl.duration // 4})"
        )

        l.text = f"{{{tags}}}{syl.text}"
        io.write_line(l)


@io.track
def leadout_effect(line: Line, syl: Syllable, l: Line):
    l.layer = 0
    l.start_time = line.start_time + syl.end_time
    l.end_time = line.end_time + line.leadout // 2

    # Original values
    original_c1 = line.styleref.color1
    original_c3 = line.styleref.color3

    # Configuration
    theme = ACTOR_THEMES.get(line.actor, ACTOR_THEMES[""])

    tags = (
        rf"\an5\pos({syl.center},{syl.middle})"
        rf"\1c{original_c1}\3c{original_c3}"
        rf"\t({l.duration-line.leadout // 2},{l.duration},\1c{theme['fade']}\3c{theme['outline']})"
        rf"\fad(0,{line.leadout // 2})"
    )
    l.text = f"{{{tags}}}{syl.text}"

    io.write_line(l)


@io.track
def romaji(line: Line, l: Line):
    for syl in Utils.all_non_empty(line.syls):
        leadin_effect(line, syl, l)
        if syl.inline_fx == "echo":
            main_echo_effect(line, syl, l)
        else:
            main_effect(line, syl, l)
        leadout_effect(line, syl, l)


@io.track
def kanji(line: Line, l: Line):
    for syl in Utils.all_non_empty(line.syls):
        leadin_effect(line, syl, l)
        if syl.inline_fx == "echo":
            main_echo_effect(line, syl, l)
        else:
            main_effect(line, syl, l)
        leadout_effect(line, syl, l)


@io.track
def translation(line: Line, l: Line):
    l.start_time = line.start_time - line.leadin // 2
    l.end_time = line.end_time + line.leadout // 2

    tags = (
        rf"\fad({line.leadin // 2}, {line.leadout // 2})"
        f"{cu.get_color_change(l, c1=True, c3=True)}"
    )

    l.text = f"{{{tags}}}{line.text}"

    io.write_line(l)


# Generating lines
for line in Utils.all_non_empty(lines):
    l = line.copy()

    # Process based on alignment (line type)
    if line.styleref.alignment >= 7:
        romaji(line, l)
    elif line.styleref.alignment >= 4:
        kanji(line, l)
    else:
        translation(line, l)

io.save()
io.open_aegisub()
