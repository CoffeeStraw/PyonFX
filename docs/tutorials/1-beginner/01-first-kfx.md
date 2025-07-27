# Tutorial: Your First KFX with PyonFX

Welcome to the beginner series! :rocket:

In this tutorial, you'll create your first real karaoke effect (KFX) using PyonFX. We'll move beyond basic text positioning to build a nice three-phase effect that makes syllables come alive on screen.

## Materials

For this tutorial, we'll work with a more complex subtitle file: [romaji_kanji_translation.ass](https://github.com/CoffeeStraw/PyonFX/blob/v1.0.0/examples/ass/romaji_kanji_translation.ass). This file contains three types of subtitle lines:

- **Romaji lines** (phonetic Japanese) - alignment 7 or higher
- **Kanji lines** (Japanese characters) - intermediate alignment  
- **Translation lines** (English) - lower alignment

Please ensure that you have downloaded and installed [Migu Font](https://www.freejapanesefont.com/migu-font-%E3%83%9F%E3%82%B0%E3%83%95%E3%82%A9%E3%83%B3%E3%83%88/), a free and publicly available Japanese font, so that the subtitles display correctly.

This tutorial will focus on the Romaji lines.

## Understanding Karaoke Effects

Before diving into code, let's understand what makes a good karaoke effect. Most follow a three-phase timing structure:

- **Leadin Phase**: Text begins transitioning slightly before the syllable timing. Think of it as a gentle "get ready" cue that prevents jarring sudden changes
- **Highlight Phase** (or *Main Effect*): This is your color change, scaling, or animation that clearly shows when to sing. It's perfectly synchronized with the vocal timing, and it's what defines the character of the karaoke style
- **Leadout Phase**: After singing ends, text gracefully transitions away rather than vanishing instantly. This maintains visual continuity and feels much more polished

In this tutorial, we'll create a simple effect that follows this pattern.

## Code Walkthrough

**0. Setup and File Loading**

We start with our familiar pattern, but with our new karaoke file:

```python
from pyonfx import Ass

# Load the karaoke file
io = Ass("romaji_kanji_translation.ass")
meta, styles, lines = io.get_data()
```

**1. Iterating and Filter Lines for Karaoke**

Unlike our previous single-line examples, we need to process selectively now. Here we'll iterate through all lines but filter for only the romaji lyrics that need karaoke effects:

```python
# Process each line
for line in lines:
    # Only apply the effect to non-commented lines with alignment 7 or higher (Romaji)
    if line.comment or line.styleref.alignment < 7:
        continue
```

This filter catches exactly what we want:

- `line.comment` skips commented-out lines
- `line.styleref.alignment < 7` targets only Romaji lines (alignment 7+), ignoring Kanji and translation lines

**2. Iterating and Filtering Syllables**

Now we set up our syllable loop:

```python hl_lines="4-11"
for line in lines:
    ...

    # Create a copy of the line for the output
    l = line.copy()

    # We'll work with syllables for karaoke effects
    for syl in line.syls:
        # Skip empty syllables
        if syl.text == "":
            continue
```

We skip empty syllables because they don't contribute visual content, but can exist in ASS files as timing placeholders.

**3. Introducing key concepts**

Before we build our effect, let's understand two important PyonFX features:

- *Introducing `line.leadin` and `line.leadout`*
	
	PyonFX calculates natural pause times between lines—`line.leadin` (gap before this line) and `line.leadout` (gap after). These give us perfect timing windows for our effects without overlapping adjacent lines.

- *Cleaner Code with f-strings*

	We're upgrading from the % formatting you've seen to raw f-strings:

	```python
	# Old way (what you've seen)
	l.text = "{\\an5\\pos(%.3f,%.3f)}%s" % (syl.center, syl.middle, syl.text)

	# New way (cleaner and more readable)
	l.text = rf"{{\an5\pos({syl.center},{syl.middle})}}{syl.text}"
	```

	The `rf` prefix means "raw f-string" - raw strings don't need double backslashes for ASS tags, and f-strings let you put variables directly inside `{}` brackets.

**4. Leadin Effect**

Let's make syllables appear gracefully before they're sung:

```python hl_lines="3-11"
for syl in line.syls:
    ...
    # LEADIN EFFECT: syllable appears before being sung
    l.layer = 0
    l.start_time = line.start_time - line.leadin // 2
    l.end_time = line.start_time + syl.start_time

	tags = rf"\an5\pos({syl.center},{syl.middle})\fad({line.leadin//2},0)"
	l.text = f"{{{tags}}}{syl.text}"

	io.write_line(l)
```

Breaking this down:

- **Layer 0**: Background layer (our highlight will go on top later)
- **Timing**: Starts halfway through the available leadin time, ends when syllable singing begins
- **Fade**: Simple fade-in using half the leadin duration

![Leadin effect visualization](imgs/leadin.gif)

**5. Highlight Effect**

Time for the main event—the syllable gets emphasized while being sung:

```python hl_lines="3-15"
for syl in line.syls:
    ...
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
```

This creates a simple "swell" effect:

- **Layer 1**: Places this on top of the leadin effect
- **Timing**: Perfectly matches the syllable's singing duration
- **Double transformation**:
	- First half: Scale to 125% with white/gray colors
	- Second half: Returns to normal size and original style colors

The result? A syllable that grows, changes color, then settles back—perfectly timed to the vocals.

![Highlight effect visualization](imgs/highlight.gif)

**6. Leadout Effect**

Finally, let's make the syllable fade gracefully after being sung:

```python hl_lines="3-11"
for syl in line.syls:
    ...
	# LEADOUT EFFECT: syllable fades after being sung
	l.layer = 0
	l.start_time = line.start_time + syl.end_time
	l.end_time = line.end_time + line.leadout // 2

	tags = rf"\an5\pos({syl.center},{syl.middle})\fad(0,{line.leadout//2})"
	l.text = f"{{{tags}}}{syl.text}"

	io.write_line(l)
```

The details:

- **Layer 0**: Back to background layer
- **Timing**: Starts when singing ends, extends into the leadout period
- **Fade**: Simple fade-out using half the available leadout time

![Leadout effect visualization](imgs/leadout.gif)

**7. Bringing it all together**

Save and preview your masterpiece:

```python
io.save()
io.open_aegisub()
```

![Complete karaoke effect](imgs/kfx.gif)

## Conclusion

Fantastic work! :tada: You've just created your first professional karaoke effect. You've learned to build a complete three-phase system that makes syllables appear, highlight, and fade with perfect timing.

The effect looks great, but I bet you noticed the code is getting complex. In the next tutorial, we'll refactor this into clean, reusable functions that will make your karaoke workflow much more efficient and maintainable.

## Full Source Code
??? abstract "Show full source code"
    ```python
    --8<-- "examples/tutorials/1_beginner/01_first_kfx.py"
    ```
