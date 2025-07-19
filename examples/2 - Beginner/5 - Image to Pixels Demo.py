"""
Image to Pixels Demo - Demonstrating the image_to_pixels function

This demo shows how to use the Convert.image_to_pixels() function to convert
an image into pixel data that can be used for ASS effects. The astronaut image
will be displayed next to the first line with appropriate fade effects.

The demo creates individual pixel elements for each non-transparent pixel in the image,
positioning them relative to the first line and applying fade effects.
"""

import os

from pyonfx import *

io = Ass("in.ass", vertical_kanji=True)
meta, styles, lines = io.get_data()

# Pixel setup
io.add_style("p", Ass.PIXEL_STYLE)

# Prepare png file
image_path = "lighthouse.png"
lighthouse_pixels = Convert.image_to_pixels(
    image_path, skip_transparent=True, width=80, height=80
)
min_x = min(p.x for p in lighthouse_pixels)
min_y = min(p.y for p in lighthouse_pixels)
max_y = max(p.y for p in lighthouse_pixels)
image_height = max_y - min_y + 1


# Check if image exists
@io.track
def image_effect(line: Line, l: Line):
    """Display the lighthouse image next to the line."""

    # Position image to the right of the line
    image_start_x = line.right + 30
    image_start_y = line.top - (image_height - line.height) // 2

    # Create pixel elements
    for pixel in lighthouse_pixels:
        # Calculate final position
        final_x = image_start_x + (pixel.x - min_x)
        final_y = image_start_y + (pixel.y - min_y)

        # Create timing
        l.start_time = line.start_time
        l.end_time = line.end_time
        l.layer = 1
        l.style = "p"

        color_tag = f"\\1c{pixel.color}"
        alpha_tag = f"\\alpha{pixel.alpha if pixel.alpha != '&H00&' else ''}"
        tags = rf"\\p1\pos({final_x},{final_y}){color_tag}{alpha_tag}\fad(300,300)"
        l.text = f"{{{tags}}}{Shape.PIXEL}"

        io.write_line(l)


@io.track
def sub(line: Line, l: Line):
    """Test effect: Convert text to shape and apply texture from 'stock_texture.jpg'."""
    l.start_time = line.start_time - line.leadin // 2
    l.end_time = line.end_time + line.leadout // 2

    fad = rf"\fad({line.leadin // 2}, {line.leadout // 2})"
    l.text = f"{{{fad}}}{line.text}"

    io.write_line(l)

    # Apply texture using the image 'stock_texture.jpg' with 'stretch' mode
    l.style = "p"
    shape_pixels = Convert.text_to_pixels(line)
    textured_pixels = shape_pixels.apply_texture("stock_texture.jpg")

    # Output each textured pixel as a separate line with a pixel drawing command
    for pixel in textured_pixels:
        # Compute absolute position for the pixel based on the original line position
        x = int(line.left) + pixel.x
        y = int(line.top) + pixel.y

        # Create a simple drawing command using \p1. This draws a tiny rectangle representing a pixel.
        l.text = f"{{\\p1\\pos({x},{y})\\1c{pixel.color}\\alpha{pixel.alpha}{fad}}}{Shape.PIXEL}"
        io.write_line(l)


# Generate lines
for line in lines[1:2]:
    # Apply image effect only to the first line
    image_effect(line, line.copy())

    # Apply subtitle effect to all lines
    sub(line, line.copy())

io.save()
io.open_aegisub()
