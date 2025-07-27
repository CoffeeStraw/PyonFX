"""
Tutorial: Creating your first Karaoke Effect (KFX)

This tutorial demonstrates how to define and apply your first karaoke effect.
We work with a .ass file containing Romaji, Kanji and Translation lines, applying the effects only to those with alignment 7 or higher (Romaji).

For each applicable line, we process each syllable to apply 3 distinct effects:
• LEADIN EFFECT: makes the syllable fade in before being sung
• HIGHLIGHT EFFECT: highlights the syllable with scaling and color transitions
• LEADOUT EFFECT: makes the syllable fade out after being sung

Exercise:
• Change the 1c and 3c tags of the main effect to see how the effect changes.
"""

from pyonfx import Ass

# Load the karaoke file
io = Ass("../../ass/romaji_kanji_translation.ass")
meta, styles, lines = io.get_data()

# Process each line
for line in lines:
    # Only apply the effect to non-commented lines with alignment 7 or higher (Romaji)
    if line.comment or line.styleref.alignment < 7:
        continue

    # Create a copy of the line for the output
    l = line.copy()

    # We'll work with syllables for karaoke effects
    for syl in line.syls:
        # Skip empty syllables
        if syl.text == "":
            continue

        # LEADIN EFFECT: syllable appears before being sung
        l.layer = 0
        l.start_time = line.start_time - line.leadin // 2
        l.end_time = line.start_time + syl.start_time

        tags = rf"\an5\pos({syl.center},{syl.middle})\fad({line.leadin//2},0)"
        l.text = f"{{{tags}}}{syl.text}"

        io.write_line(l)

        # HIGHLIGHT EFFECT: main effect when syllable is sung
        l.layer = 1
        l.start_time = line.start_time + syl.start_time
        l.end_time = line.start_time + syl.end_time

        tags = (
            rf"\an5\pos({syl.center},{syl.middle})"
            rf"\t(0,{syl.duration // 2},\fscx125\fscy125\1c&HFFFFFF&\3c&HABABAB&)"
            rf"\t({syl.duration // 2},{syl.duration},\fscx100\fscy100\1c{line.styleref.color1}\3c{line.styleref.color3})"
        )
        l.text = f"{{{tags}}}{syl.text}"

        io.write_line(l)

        # LEADOUT EFFECT: syllable fades after being sung
        l.layer = 0
        l.start_time = line.start_time + syl.end_time
        l.end_time = line.end_time + line.leadout // 2

        tags = rf"\an5\pos({syl.center},{syl.middle})\fad(0,{line.leadout//2})"
        l.text = f"{{{tags}}}{syl.text}"

        io.write_line(l)

# Save and preview
io.save()
io.open_aegisub()
