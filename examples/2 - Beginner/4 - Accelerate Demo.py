from pyonfx import *
from pyonfx.utils import FrameUtility

# Parameters
HEIGHT = 700
DURATION_MS = 4000
DURATION_STILL_MS = 500
HORIZONTAL_DISTANCE = 300
CIRCLE_RADIUS = 15
MARGIN = 20

# All available accelerators
ACC_PRESETS = [
    1.0,  # Linear
    0.5,  # Power 0.5
    1.5,  # Power 1.5
    "in_back",
    "out_back",
    "in_out_back",
    "in_bounce",
    "out_bounce",
    "in_out_bounce",
    "in_circ",
    "out_circ",
    "in_out_circ",
    "in_cubic",
    "out_cubic",
    "in_out_cubic",
    "in_elastic",
    "out_elastic",
    "in_out_elastic",
    "in_expo",
    "out_expo",
    "in_out_expo",
    "in_quad",
    "out_quad",
    "in_out_quad",
    "in_quart",
    "out_quart",
    "in_out_quart",
    "in_quint",
    "out_quint",
    "in_out_quint",
    "in_sine",
    "out_sine",
    "in_out_sine",
]


def generate_color_palette(count):
    import colorsys

    colors = []
    for i in range(count):
        hue = i / count
        r, g, b = [int(x * 255) for x in colorsys.hsv_to_rgb(hue, 1, 1)]
        colors.append(f"&H{b:02X}{g:02X}{r:02X}&")
    return colors


COLORS = generate_color_palette(len(ACC_PRESETS))

io = Ass("in.ass")
meta, styles, lines = io.get_data()
template_line = lines[1].copy()
CIRCLE = Shape.ellipse(CIRCLE_RADIUS, CIRCLE_RADIUS)

# Single FrameUtility for all circles
FU = FrameUtility(0, DURATION_MS + DURATION_STILL_MS * 2, meta.timestamps)
VERTICAL_SPACING = HEIGHT / (len(ACC_PRESETS) + 1)

for start, end, i, n in FU:
    for idx, (acc, color) in enumerate(zip(ACC_PRESETS, COLORS)):
        l = template_line.copy()
        l.start_time = start
        l.end_time = end
        l.layer = 0

        # Calculate vertical position
        y = MARGIN + VERTICAL_SPACING * (idx)

        # Use FU.add with the right acceleration for this circle
        x_offset = FU.add(DURATION_STILL_MS, DURATION_MS, HORIZONTAL_DISTANCE, acc)
        x = MARGIN * 6 + x_offset

        l.text = (
            f"{{\\an7\\pos({x},{y})\\p1\\1c{color}\\bord0}}{CIRCLE}"
            f"{{\\r\\p0\\an7\\fs15}}{acc}"
        )
        io.write_line(l)

io.save()
io.open_aegisub()
