import os 
import pytest
from pyonfx import *

# Get ass path
dir_path = os.path.dirname(os.path.realpath(__file__))
path_ass = os.path.join(dir_path, "Ass", "in.ass")

# Extract infos from ass file
io = Ass(path_ass)
meta, styles, lines = io.get_data()


def test_interpolation():
	res = Utils.interpolate(0.9, "&H000000&", "&HFFFFFF&")
	assert res == "&HE5E5E5&"

def test_frames():
	#print("\n")
	FU = FrameUtility(0, 105, 40)
	#print(FU.start_time)
	for s, e, i, n in FU:
		fsc = 100
		fsc += FU.add(0, 50, 50)
		fsc += FU.add(50, 100, -50)
		#print(fsc, s, e, i, n)
	
	#print("-----")
	#print(FU.start_time)

	for s, e, i, n in FU:
		fsc = 100
		fsc += FU.add(0, 50, 50)
		fsc += FU.add(50, 100, -50)
		#print(fsc, s, e, i, n)
