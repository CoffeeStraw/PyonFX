from pyonfx import *

Settings.mpv = False
Settings.aegisub = True

io = Ass("in.ass")
meta, styles, lines = io.get_data()

line = Line.copy(lines[1])
line.text = "{\\an5\\pos(%.3f,%.3f)\\clip(%s)}%s" % (line.center, line.middle, Convert.text_to_clip(line, an=5), line.text)
io.write_line(line)

io.save()