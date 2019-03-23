import os 
import pytest
from pyonfx import *

# Get ass path
dir_path = os.path.dirname(os.path.realpath(__file__))
path_ass = os.path.join(dir_path, "Ass", "in.ass")

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
	# Tests if all the line values are taken correctly
	line = lines[1]
	assert line.comment == False
	assert line.layer == 0
	assert line.start_time == Convert.time("0:00:14.24")
	assert line.end_time == Convert.time("0:00:24.23")
	assert line.duration == Convert.time("0:00:24.23") - Convert.time("0:00:14.24")
	assert line.leadin == 1000.1
	assert line.leadout == lines[2].start_time - lines[1].end_time
	assert line.style == "Romaji"
	assert line.actor == ""
	assert line.margin_l == 0
	assert line.margin_r == 0
	assert line.margin_v == 0
	assert line.effect == ""
	assert line.raw_text == "{\\k56}su{\\k13}re{\\k22}chi{\\k36}ga{\\k48}u{\\k25} {\\k34}ko{\\k33}to{\\k50}ba {\\k15}no {\\k17}u{\\k34}ra {\\k46}ni{\\k33} {\\k28}to{\\k36}za{\\k65}sa{\\k33}{\\k30}re{\\k51}ta{\\k16} {\\k33}ko{\\k33}ko{\\k78}ro {\\k15}no {\\k24}ka{\\k95}gi"
	assert line.text == "surechigau kotoba no ura ni tozasareta kokoro no kagi"
	# Values taken from YutilsCore to test
	assert line.width == 941.703125
	assert line.height == 48.0
	assert line.ascent == 36.984375
	assert line.descent == 11.015625
	assert line.internal_leading == 13.59375
	assert line.external_leading == 3.09375
	assert line.x == line.center
	assert line.y == line.top
	assert line.left == 169.1484375
	assert line.center == 640.0
	assert line.right == 1110.8515625
	assert line.top == 25.0
	assert line.middle == 49.0
	assert line.bottom == 73.0
