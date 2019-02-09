import os 
import pytest
from pyonfx import *

# Get ass path
dir_path = os.path.dirname(os.path.realpath(__file__))
path_ass = os.path.join(dir_path, "Ass", "in.ass")

# Extract infos from ass file
io = Ass(path_ass)
meta, styles, lines = io.get_data()

def test_coloralpha():
	assert Convert.coloralpha(0) == "&HFF&"
	assert Convert.coloralpha("&HFF&") == 0

	assert Convert.coloralpha("&H0000FF&") == (255, 0, 0)
	assert Convert.coloralpha(255, 0, 0) == "&H0000FF&"

	assert Convert.coloralpha("&H0000FFFF") == (255, 255, 0, 255)
	assert Convert.coloralpha(255, 255, 0, 255) == "&H0000FFFF"
