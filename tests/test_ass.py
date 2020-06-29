import os
from pyonfx import *

# Get ass path used for tests
dir_path = os.path.dirname(os.path.realpath(__file__))
path_ass = os.path.join(dir_path, "Ass", "ass_core.ass")

# Extract infos from ass file
io = Ass(path_ass)
meta, styles, lines = io.get_data()

def test_meta_values():
	# Tests if all the meta values are taken correctly
	# assert meta.wrap_style == 0 					# -> not in this .ass, so let's comment this
	# assert meta.scaled_border_and_shadow == True  # -> not in this .ass, so let's comment this
	assert meta.play_res_x == 1280
	assert meta.play_res_y == 720
	# assert meta.audio == "" 						# -> not in this .ass, so let's comment this
	assert meta.video == "?dummy:23.976000:2250:1920:1080:11:135:226:c"

def test_line_values():
	# Comment recognition
	assert lines[0].comment == True
	assert lines[1].comment == False

	# Line fields
	assert lines[0].layer == 42
	assert lines[1].layer == 0

	assert lines[0].style == "Default"
	assert lines[1].style == "Normal"

	assert lines[0].actor == "Test"
	assert lines[1].actor == ""

	assert lines[0].effect == "Test; Wow"
	assert lines[1].effect == ""

	assert lines[0].margin_l == 1
	assert lines[1].margin_l == 0

	assert lines[0].margin_r == 2
	assert lines[1].margin_r == 0

	assert lines[0].margin_v == 3
	assert lines[1].margin_v == 50

	assert lines[1].start_time == Convert.time("0:00:00.00")
	assert lines[1].end_time == Convert.time("0:00:09.99")
	assert lines[1].duration == Convert.time("0:00:09.99") - Convert.time("0:00:00.00")
	
	assert lines[11].raw_text == "{\\k56}{\\1c&HFFFFFF&}su{\\k13}re{\\k22}chi{\\k36}ga{\\k48}u {\\k25\\-Pyon}{\\k34}ko{\\k33}to{\\k50}ba {\\k15}no {\\k17}u{\\k34}ra {\\k46}ni{\\k33} {\\k28}to{\\k36}za{\\k65}sa{\\1c&HFFFFFF&\\k33\\1c&HFFFFFF&\\k30\\1c&HFFFFFF&}re{\\k51\\-FX}ta{\\k16} {\\k33}ko{\\k33}ko{\\k78}ro {\\k15}no {\\k24}ka{\\k95}gi"
	assert lines[11].text == "surechigau kotoba no ura ni tozasareta kokoro no kagi"

	# Normal style (no bold, italic and with a normal fs)
	assert round(lines[1].width) == round(437.75)
	assert round(lines[1].height) == round(48.0)
	assert round(lines[1].ascent) == round(36.984375)
	assert round(lines[1].descent) == round(11.015625)
	assert round(lines[1].internal_leading) == round(13.59375) or lines[1].internal_leading == 0.0
	assert round(lines[1].external_leading) == round(3.09375) or lines[1].external_leading == 0.0
	assert round(lines[1].x) == round(lines[1].center)
	assert round(lines[1].y) == round(lines[1].top)
	assert round(lines[1].left) == round(421.125)
	assert round(lines[1].center) == round(640.0)
	assert round(lines[1].right) == round(858.875)
	assert round(lines[1].top) == round(50.0)
	assert round(lines[1].middle) == round(74.0)
	assert round(lines[1].bottom) == round(98.0)

	# Bold style
	assert round(lines[2].width) == round(461.609375)
	assert round(lines[2].height) == round(48.0)

	# Italic style
	assert round(lines[3].width) == round(437.75)
	assert round(lines[3].height) == round(48.0)

	# Bold-italic style
	assert round(lines[4].width) == round(461.609375)
	assert round(lines[4].height) == round(48.0)

	# Normal-spaced style
	assert round(lines[5].width) == round(572.75)
	assert round(lines[5].height) == round(48.0)

	# Normal - fscx style
	assert round(lines[6].width) == round(612.8499999999999)
	assert round(lines[6].height) == round(48.0)

	# Normal - fscy style
	assert round(lines[7].width) == round(437.75)
	assert round(lines[7].height) == round(67.19999999999999)

	# Normal - Big FS
	assert round(lines[8].width) == round(820.796875)
	assert round(lines[8].height) == round(90.0)

	# Normal - Big FS - Spaced
	assert round(lines[9].width) == round(1090.796875)
	assert round(lines[9].height) == round(90.0)

	# Bold - Text with non latin characters (kanji)
	assert round(lines[10].width) == round(309.65625)
	assert round(lines[10].height) == round(48.0)

	# Bold - Text with some tags
	assert round(lines[11].width) == round(941.703125)
	assert round(lines[11].height) == round(48.0)

	# Bold - Vertical Text
	assert round(lines[12].width) == round(31.546875)
	assert round(lines[12].height) == round(396.0)
