# If you're trying this example having downloaded the repository
# and not only installed PyonFX, uncomment the following lines:
# import sys
# sys.path.insert(0,'../')

from pyonfx import *

io = Ass("..\\tests\\Ass\\in.ass")
meta, styles, lines = io.get_data()

def romaji_kanji(line, l):
	# Leadin Effect
	for syli, syl in Utils.all_non_empty(line.syls):
		l.layer = 0
		
		l.start_time = line.start_time - line.leadin/2
		l.end_time = line.start_time + syl.start_time
		l.dur = l.end_time - l.start_time
		
		l.text = "{\\an5\\pos(%.3f,%.3f)\\fad(%d,0)}%s" % (
			syl.center, syl.middle, line.leadin/2, syl.text)
		
		io.write_line(l)

	# Main Effect
	for syli, syl in Utils.all_non_empty(line.syls):
		l.layer = 1
		
		l.start_time = line.start_time + syl.start_time
		l.end_time = line.start_time + syl.end_time
		l.dur = l.end_time - l.start_time
		
		l.text = "{\\an5\\pos(%.3f,%.3f)"\
				 "\\t(0,%d,0.5,\\1c&HFFFFFF&\\3c&HABABAB&\\fscx125\\fscy125)"\
				 "\\t(%d,%d,1.5,\\fscx100\\fscy100\\1c%s\\3c%s)}%s" % (
			syl.center, syl.middle,
			l.dur/3, l.dur/3, l.dur, line.styleref.color1, line.styleref.color3, syl.text)
		
		io.write_line(l)

	# Leadout Effect
	for syli, syl in Utils.all_non_empty(line.syls):
		l.layer = 0
		
		l.start_time = line.start_time + syl.end_time
		l.end_time = line.end_time + line.leadout/2
		l.dur = l.end_time - l.start_time
		
		l.text = "{\\an5\\pos(%.3f,%.3f)\\fad(0,%d)}%s" % (
			syl.center, syl.middle, line.leadout/2, syl.text)
		
		io.write_line(l)

def lyrics(line, l):
	# Translation Effect
	l.start_time = line.start_time - line.leadin/2
	l.end_time = line.end_time + line.leadout/2
	l.dur = l.end_time - l.start_time
	
	l.text = "{\\fad(%d,%d)}%s" % (
		line.leadin/2, line.leadout/2, line.text_stripped)
	
	io.write_line(l)

for li, line in enumerate(lines):
	# Generating lines
	if line.styleref.alignment >= 4:
		romaji_kanji(line, line.copy())
	elif line.styleref.alignment <= 3:
		lyrics(line, line.copy())

io.save()