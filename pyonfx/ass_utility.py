# -*- coding: utf-8 -*-
# PyonFX: An easy way to do KFX and complex typesetting based on subtitle format ASS (Advanced Substation Alpha).
# Copyright (C) 2019 Antonio Strippoli (CoffeeStraw/YellowFlash)
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# PyonFX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see http://www.gnu.org/licenses/.

import os
import sys
import time
import re
import copy
from .font_utility import Font
from .convert import Convert
from .settings import Settings


class Meta:
	"""Meta object contains informations about the Ass.
	
	More info about each of them can be found on http://docs.aegisub.org/manual/Styles

	Attributes:
		wrap_style (int): Determines how line breaking is applied to the subtitle line
		scaled_border_and_shadow (bool): Determines if it has to be used script resolution (*True*) or video resolution (*False*) to scale border and shadow
		play_res_x (int): Video Width
		play_res_y (int): Video Height
		audio (str): Loaded audio path (absolute)
		video (str): Loaded video path (absolute)
    """
	wrap_style 				 = 0
	scaled_border_and_shadow = True
	play_res_x 				 = 0
	play_res_y 				 = 0
	audio 					 = ""
	video 					 = ""

	def __repr__(self):
		return f"Meta Object {id(self)}:\n\tWrap Style: {self.wrap_style}\n\tScaled Border And Shadow: {self.scaled_border_and_shadow}\n\t"\
			   f"Play Resolution X: {self.play_res_x}\n\tPlay Resolution Y: {self.play_res_y}\n\t"\
			   f"Audio: {self.audio}\n\tVideo: {self.video}"


class Style:
	"""Style object contains a set of typographic formatting rules that is applied to dialogue lines. 
	
	More info about styles can be found on http://docs.aegisub.org/3.2/ASS_Tags/.

	Attributes:
		fontname (str): Font name
		fontsize (int): Font size in points
		color1 (str): Primary color (fill)
		alpha1 (str): Trasparency of color1
		color2 (str): Secondary color (secondary fill, for karaoke effect)
		alpha2 (str): Trasparency of color2
		color3 (str): Outline (border) color
		alpha3 (str): Trasparency of color3
		color4 (str): Shadow color
		alpha4 (str): Trasparency of color4
		bold (bool): Font with bold
		italic (bool): Font with italic
		underline (bool): Font with underline
		strikeout (bool): Font with strikeout
		scale_x (float): Text stretching in the horizontal direction
		scale_y (float): Text stretching in the vertical direction
		spacing (float): Horizontal spacing between letters
		angle (float): Rotation of the text
		border_style (bool): *True* for opaque box, *False* for standard outline
		outline (float): Border thickness value
		shadow (float): How far downwards and to the right a shadow is drawn
		alignment (int): Alignment of the text
		margin_l (int): Distance from the left of the video frame
		margin_r (int): Distance from the right of the video frame
		margin_v (int): Distance from the bottom (or top if alignment >= 7) of the video frame
		encoding (int): Codepage used to map codepoints to glyphs
    """
	fontname 			= ""
	fontsize 			= 0
	color1 				= ""
	alpha1 				= ""
	color2 				= ""
	alpha2 				= ""
	color3 				= ""
	alpha3 				= ""
	color4 				= ""
	alpha4 				= ""
	bold 				= False
	italic 				= False
	underline 			= False
	strikeout 			= False
	scale_x 			= 100.0
	scale_y 			= 100.0
	spacing 			= 0.0
	angle 				= 0.0
	border_style 		= False
	outline 			= 2.0
	shadow 				= 0.0
	alignment 			= 8
	margin_l 			= 30
	margin_r 			= 30
	margin_v 			= 30
	encoding 			= 1

	def __repr__(self):
		return str(self.__dict__)


class Line:
	"""Line object contains informations about a single line in the Ass.

	Note:
		(*) = This field is available only if :class:`extended<Ass>` = True

	Attributes:
		comment (bool): If *True*, this line will not be displayed on the screen.
		layer (int): Layer for the line. Higher layer numbers are drawn on top of lower ones.
		start_time (int): Line start time (in milliseconds).
		end_time (int): Line end time (in milliseconds).
		duration (int): Line duration (in milliseconds) (*).
		leadin (float): Time between this line and the previous one (in milliseconds; first line = 1000.1) (*).
		leadout (float): Time between this line and the next one (in milliseconds; first line = 1000.1) (*).
		style (str): Style name used for this line.
		styleref (obj): Reference to the Style object of this line (*).
		actor (str): Actor field.
		margin_l (int): Left margin for this line.
		margin_r (int): Right margin for this line.
		margin_v (int): Vertical margin for this line.
		effect (str): Effect field.
		text (str): Line raw text.
		text_stripped (str): Line stripped text.
		width (float): Line text width (*).
		height (float): Line text height (*).
		ascent (float): Line font ascent (*).
		descent (float): Line font descent (*).
		internal_leading (float): Line font internal lead (*).
		external_leading (float): Line font external lead (*).
		x (float): Line text position horizontal (depends on alignment) (*).
		y (float): Line text position vertical (depends on alignment) (*).
		left (float): Line text position left (*).
		center (float): Line text position center (*).
		right (float): Line text position right (*).
		top (float): Line text position top (*).
		middle (float): Line text position middle (*).
		bottom (float): Line text position bottom (*).
		words (list): List containing objects :class:`Word` in this line (*).
		syls (list): List containing objects :class:`Syllable` in this line (if available) (*).
		chars (list): List containing objects :class:`Char` in this line (*).
	"""
	comment 			= False
	layer 				= 0
	start_time 			= 0
	end_time			= 0
	style 				= ""
	actor 				= ""
	margin_l 			= 0
	margin_r 			= 0
	margin_v 			= 0
	effect 				= ""
	text  				= ""
	text_stripped 		= ""

	def __repr__(self):
		return str(self.__dict__)

	def copy(self):
		"""
		Returns:
			A deep copy of this object (line)
		"""
		return copy.deepcopy(self)


class Word:
	"""Word object contains informations about a single word of a line in the Ass.

	A word can be defined as some text with some optional space before or after 
	(e.g.: In the string "What a beautiful world!", "beautiful" and "world" are both distinct words).

	Attributes:
		start_time (int): Word start time (same as line start time) (in milliseconds).
		end_time (int): Word end time (same as line end time) (in milliseconds).
		duration (int): Word duration (same as line duration) (in milliseconds).
		text (str): Word text.
		prespace (int): Word free space before text.
		postspace (int): Word free space after text.
		width (float): Word text width.
		height (float): Word text height.
		ascent (float): Word font ascent.
		descent (float): Word font descent.
		internal_leading (float): Word font internal lead.
		external_leading (float): Word font external lead.
		x (float): Word text position horizontal (depends on alignment).
		y (float): Word text position vertical (depends on alignment).
		left (float): Word text position left.
		center (float): Word text position center.
		right (float): Word text position right.
		top (float): Word text position top.
		middle (float): Word text position middle.
		bottom (float): Word text position bottom.
	"""
	start_time 			= 0
	end_time 			= 0
	duration 			= 0

	text 				= ""

	prespace 			= 0
	postspace 			= 0

	width 				= 0
	height 				= 0

	ascent 				= 0
	descent 			= 0

	internal_leading 	= 0
	external_leading 	= 0

	x 					= 0
	y 					= 0

	left 				= 0
	center 				= 0
	right 				= 0

	top 				= 0
	middle 				= 0
	bottom 				= 0

	def __repr__(self):
		return str(self.__dict__)


class Syllable:
	"""Syllable object contains informations about a single syl of a line in the Ass.
	
	A syl can be defined as some text after a karaoke tag (k, ko, kf) 
	(e.g.: In "{\\k0}Hel{\\k0}lo {\\k0}Pyon{\\k0}FX {\\k0}users!", "Pyon" and "FX" are distinct syllables),

	Attributes:
		word_i (int): Syllable word index (e.g.: In line text "{\\k0}Hel{\\k0}lo {\\k0}Pyon{\\k0}FX {\\k0}users!", syl "Pyon" will have word_i=1).
		start_time (int): Syllable start time (in milliseconds).
		end_time (int): Syllable end time (in milliseconds).
		duration (int): Syllable duration (in milliseconds).
		text (str): Syllable text.
		inline_fx (str): Syllable inline effect (marked as \\-EFFECT in karaoke-time).
		prespace (int): Syllable free space before text.
		postspace (int): Syllable free space after text.
		width (float): Syllable text width.
		height (float): Syllable text height.
		ascent (float): Syllable font ascent.
		descent (float): Syllable font descent.
		internal_leading (float): Syllable font internal lead.
		external_leading (float): Syllable font external lead.
		x (float): Syllable text position horizontal (depends on alignment).
		y (float): Syllable text position vertical (depends on alignment).
		left (float): Syllable text position left.
		center (float): Syllable text position center.
		right (float): Syllable text position right.
		top (float): Syllable text position top.
		middle (float): Syllable text position middle.
		bottom (float): Syllable text position bottom.
	"""
	word_i 				= 0

	start_time 			= 0
	end_time 			= 0
	duration 			= 0

	text 				= ""
	inline_fx 			= ""

	prespace 			= 0
	postspace 			= 0

	width 				= 0
	height 				= 0
	
	ascent 				= 0
	descent 			= 0
	
	internal_leading 	= 0
	external_leading 	= 0
	
	x 					= 0
	y 					= 0

	left 				= 0
	center 				= 0
	right 				= 0

	top 				= 0
	middle 				= 0
	bottom 				= 0

	def __repr__(self):
		return str(self.__dict__)


class Char:
	"""Char object contains informations about a single char of a line in the Ass.
	
	A char is defined by some text between two karaoke tags (k, ko, kf).

	Attributes:
		word_i (int): Char word index (e.g.: In line text "Hello PyonFX users!", letter "u" will have word_i=2).
		syl_i (int): Char syl index (e.g.: In line text "{\\k0}Hel{\\k0}lo {\\k0}Pyon{\\k0}FX {\\k0}users!", letter "F" will have syl_i=3).
		syl_char_i (int): Char invidual syl index (e.g.: In line text "{\\k0}Hel{\\k0}lo {\\k0}Pyon{\\k0}FX {\\k0}users!", letter "e" of "users" will have syl_char_i=2).
		start_time (int): Char start time (in milliseconds).
		end_time (int): Char end time (in milliseconds).
		duration (int): Char duration (in milliseconds).
		text (str): Char text.
		inline_fx (str): Char inline effect (marked as \\-EFFECT in karaoke-time).
		prespace (int): Char free space before text.
		postspace (int): Char free space after text.
		width (float): Char text width.
		height (float): Char text height.
		ascent (float): Char font ascent.
		descent (float): Char font descent.
		internal_leading (float): Char font internal lead.
		external_leading (float): Char font external lead.
		x (float): Char text position horizontal (depends on alignment).
		y (float): Char text position vertical (depends on alignment).
		left (float): Char text position left.
		center (float): Char text position center.
		right (float): Char text position right.
		top (float): Char text position top.
		middle (float): Char text position middle.
		bottom (float): Char text position bottom.
	"""
	word_i 				= -1
	syl_i 				= -1
	syl_char_i 			= -1

	start_time 			= 0
	end_time 			= 0
	duration 			= 0

	text 				= ""

	width 				= 0
	height 				= 0
	
	ascent 				= 0
	descent 			= 0
	
	internal_leading 	= 0
	external_leading 	= 0
	
	x 					= 0
	y 					= 0

	left 				= 0
	center 				= 0
	right 				= 0

	top 				= 0
	middle 				= 0
	bottom 				= 0

	def __repr__(self):
		return str(self.__dict__)


class Ass:
	"""Contains all the informations about a file in the ASS format and the methods to work with it.
	
	Usually you will create an Ass object and use it for input and output (see example_ section).
	PyonFX set automatically an absolute path for all the info in the output, so that wherever you will 
	put your generated file, it will always take the right path for the video and the audio.

	Args:
		path_input (str): Path for the input file (either relative or absolute).
		path_output (str): Path for the output file (either relative or absolute) (DEFAULT: "Output.ass").
		extended (bool): Calculate more informations from lines (usually you will not have to touch this).
		vertical_kanji (bool): If True, line text with alignment 4, 5 or 6 will be positioned vertically.

	Attributes:
		path_input (str): Path for input file (absolute).
		path_output (str): Path for output file (absolute).
		meta (:class:`Meta`): Contains informations about the ASS given.
		styles (list of :class:`Style`): Contains all the styles in the ASS given.
		lines (list of :class:`Line`): Contains all the lines (events) in the ASS given.

	.. _example:
	Example:
		>>> io = Ass("in.ass")
		>>> meta, styles, lines = io.get_data()

    """
	def __init__(self, path_input="", path_output="Output.ass", extended=True, vertical_kanji=True):
		# Starting to take process time
		self.__plines = 0
		self.__ptime = time.time()

		self.meta, self.styles, self.lines = Meta(), {}, []
		# Getting absolute sub file path
		dirname = os.path.dirname(os.path.abspath(sys.argv[0]))
		if not os.path.isabs(path_input):
			path_input = os.path.join(dirname, path_input)

		# Getting absolute output file path
		if path_output == "Output.ass":
			path_output = os.path.join(dirname, path_output)
		elif not os.path.isabs(path_output):
			path_output = os.path.join(dirname, path_output)

		self.path_input = path_input
		self.path_output = path_output

		# Checking sub file validity (does it exists?)
		if not os.path.isfile(path_input):
			raise FileNotFoundError("Invalid path for the Subtitle file: %s" % path_input)

		self.meta.sub = path_input
		section = ""
		self.__output = [] 
		for line in open(self.meta.sub, "r", encoding="utf-8-sig"):
			# Getting section
			section_pattern = re.compile(r"^\[([^\]]*)")
			if section_pattern.match(line):
				# Updating section
				section = section_pattern.match(line).group(1)
				# Appending line to output
				self.__output.append(line)

			# Parsing Meta data
			elif section == "Script Info" or section == "Aegisub Project Garbage":
				# Internal function that tries to get the absolute path for media files in meta
				def get_media_abs_path(subfile, mediafile):
					if not os.path.isfile(mediafile):
						tmp = mediafile
						media_dir = os.path.dirname(subfile)
						while mediafile.startswith("../"):
							media_dir = os.path.dirname(media_dir)
							mediafile = mediafile[3:]

						mediafile = os.path.normpath("%s%s%s" % (media_dir, os.sep, mediafile))
						if not os.path.isfile(mediafile):
							mediafile = tmp
					return mediafile

				# Switch
				if re.match(r"^WrapStyle: *?(\d+)$", line):
					self.meta.wrap_style = int(line[11:].strip())
				elif re.match(r"^ScaledBorderAndShadow: *?(.+)$", line):
					self.meta.scaled_border_and_shadow = line[23:].strip() == "yes"
				elif re.match(r"^PlayResX: *?(\d+)$", line):
					self.meta.play_res_x = int(line[10:].strip())
				elif re.match(r"^PlayResY: *?(\d+)$", line):
					self.meta.play_res_y = int(line[10:].strip())
				elif re.match(r"^Audio File: *?(.*)$", line):
					self.meta.audio = get_media_abs_path(self.meta.sub, line[11:].strip())
					line = "Audio File: %s\n" % self.meta.audio
				elif re.match(r"^Video File: *?(.*)$", line):
					self.meta.video = get_media_abs_path(self.meta.sub, line[11:].strip())
					line = "Video File: %s\n" % self.meta.video

				# Appending line to output
				self.__output.append(line)
			# Parsing Styles
			elif section == "V4+ Styles":
				# Appending line to output
				self.__output.append(line)
				style = re.match(r"^Style: (.+?)$", line)

				if style:
					# Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour,
					# Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle,
					# BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
					style = [el for el in style.group(1).split(',')]
					tmp = Style()
					
					tmp.fontname = style[1]
					tmp.fontsize = float(style[2])

					r, g, b, a = Convert.coloralpha(style[3])
					tmp.color1 = Convert.coloralpha(r, g, b)
					tmp.alpha1 = Convert.coloralpha(a)
					
					r, g, b, a = Convert.coloralpha(style[4])
					tmp.color2 = Convert.coloralpha(r, g, b)
					tmp.alpha2 = Convert.coloralpha(a)
					
					r, g, b, a = Convert.coloralpha(style[5])
					tmp.color3 = Convert.coloralpha(r, g, b)
					tmp.alpha3 = Convert.coloralpha(a)
					
					r, g, b, a = Convert.coloralpha(style[6])
					tmp.color4 = Convert.coloralpha(r, g, b)
					tmp.alpha4 = Convert.coloralpha(a)

					tmp.bold = style[7] == "-1"
					tmp.italic = style[8] == "-1"
					tmp.underline = style[9] == "-1"
					tmp.strikeout = style[10] == "-1"
					
					tmp.scale_x = float(style[11])
					tmp.scale_y = float(style[12])
					
					tmp.spacing = float(style[13])
					tmp.angle = float(style[14])
					
					tmp.border_style = style[15] == "3"
					tmp.outline = float(style[16])
					tmp.shadow = float(style[17])
					
					tmp.alignment = int(style[18])
					tmp.margin_l = float(style[19])
					tmp.margin_r = float(style[20])
					tmp.margin_v = float(style[21])
					
					tmp.encoding = int(style[22])

					self.styles[style[0]] = tmp
			# Parsing Dialogues
			elif section == "Events":
				# Appending line to output (commented)
				self.__output.append(re.sub(r"^(Dialogue|Comment):", "Comment:", line))

				# Analyzing line
				line = re.match(r"^(Dialogue|Comment): (.+?)$", line)

				if line:
					# Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
					tmp = Line()
					tmp.comment = line.group(1) == "Comment"
					line = [el for el in line.group(2).split(',')]

					tmp.layer = int(line[0])

					tmp.start_time = Convert.time(line[1])
					tmp.end_time = Convert.time(line[2])
					
					tmp.style = line[3]
					tmp.actor = line[4]
					
					tmp.margin_l = int(line[5])
					tmp.margin_r = int(line[6])
					tmp.margin_v = int(line[7])
					
					tmp.effect = line[8]
					
					tmp.text = ','.join(line[9:])

					self.lines.append(tmp)


		# Adding informations to lines and meta?
		if extended:
			lines_by_styles = {}
			# Let the fun begin (Pyon!)
			for li, line in enumerate(self.lines):				
				try:
					line.styleref = self.styles[line.style]
				except KeyError:
					line.styleref = None

				# Append dialog to styles (for leadin and leadout later)
				if line.style not in lines_by_styles:
					lines_by_styles[line.style] = []
				lines_by_styles[line.style].append(line)

				line.duration = line.end_time - line.start_time
				line.text_stripped = re.sub(r"\{.*?\}", "", line.text)

				# Add dialog text sizes and positions (if possible)
				if line.styleref:
					font = Font(line.styleref)
					line.width, line.height = font.get_text_extents(line.text_stripped)
					line.ascent, line.descent, line.internal_leading, line.external_leading = font.get_metrics()
					if self.meta.play_res_x > 0 and self.meta.play_res_y > 0:
						# Horizontal position
						if (line.styleref.alignment-1) % 3 == 0:
							line.left = line.margin_l if line.margin_l != 0 else line.styleref.margin_l
							line.center = line.left + line.width / 2
							line.right = line.left + line.width
							line.x = line.left
						elif (line.styleref.alignment-2) % 3 == 0:
							line.left = self.meta.play_res_x / 2 - line.width / 2
							line.center = line.left + line.width / 2
							line.right = line.left + line.width
							line.x = line.center
						else:
							line.left = self.meta.play_res_x - (line.margin_r if line.margin_r != 0 else line.styleref.margin_r) - line.width
							line.center = line.left + line.width / 2
							line.right = line.left + line.width
							line.x = line.right
						
						# Vertical position
						if line.styleref.alignment > 6:
							line.top = line.margin_v if line.margin_v != 0 else line.styleref.margin_v
							line.middle = line.top + line.height / 2
							line.bottom = line.top + line.height
							line.y = line.top
						elif line.styleref.alignment > 3:
							line.top = self.meta.play_res_y / 2 - line.height / 2
							line.middle = line.top + line.height / 2
							line.bottom = line.top + line.height
							line.y = line.middle
						else:
							line.top = self.meta.play_res_y - (line.margin_v if line.margin_v != 0 else line.styleref.margin_v) - line.height
							line.middle = line.top + line.height / 2
							line.bottom = line.top + line.height
							line.y = line.bottom
					
					# Calculating space width
					space_width = font.get_text_extents(" ")[0]
				
					# Adding words
					line.words = []

					for prespace, word_text, postspace in re.findall(r"(\s*)(\w+)(\s*)", line.text_stripped):
						word = Word()

						word.start_time = line.start_time
						word.end_time = line.end_time
						word.duration = line.duration

						word.text = word_text
						
						word.prespace = len(prespace)
						word.postspace = len(postspace)

						word.width, word.height = font.get_text_extents(word.text)
						word.ascent, word.descent, word.internal_leading, word.external_leading = font.get_metrics()

						line.words.append(word)

					# Calculate word positions with all words data already available
					if len(line.words) > 0 and self.meta.play_res_x > 0 and self.meta.play_res_y > 0:
						if line.styleref.alignment > 6 or line.styleref.alignment < 4:
							cur_x = line.left
							for word in line.words:
								# Horizontal position
								cur_x = cur_x + word.prespace * space_width
								
								word.left = cur_x
								word.center = word.left + word.width / 2
								word.right = word.left + word.width
								
								if (line.styleref.alignment-1) % 3 == 0:
									word.x = word.left
								elif (line.styleref.alignment-2) % 3 == 0:
									word.x = word.center
								else:
									word.x = word.right

								# Vertical position
								word.top = line.top
								word.middle = line.middle
								word.bottom = line.bottom
								word.y = line.y
								
								# Updating cur_x
								cur_x = cur_x + word.width + word.postspace * space_width
						else:
							max_width, sum_height = 0, 0
							for word in line.words:
								max_width = max(max_width, word.width)
								sum_height = sum_height + word.height

							cur_y = x_fix = self.meta.play_res_y / 2 - sum_height / 2
							for word in line.words:
								# Horizontal position
								x_fix = (max_width - word.width) / 2
								
								if line.styleref.alignment == 4:
									word.left = line.left + x_fix
									word.center = word.left + word.width / 2
									word.right = word.left + word.width
									word.x = word.left
								elif line.styleref.alignment == 5:
									word.left = self.meta.play_res_x / 2 - word.width / 2
									word.center = word.left + word.width / 2
									word.right = word.left + word.width
									word.x = word.center
								else:
									word.left = line.right - word.width - x_fix
									word.center = word.left + word.width / 2
									word.right = word.left + word.width
									word.x = word.right

								# Vertical position
								word.top = cur_y
								word.middle = word.top + word.height / 2
								word.bottom = word.top + word.height
								word.y = word.middle
								cur_y = cur_y + word.height


					# Add dialog text chunks, to create syllables
					text_chunks = []
					tag_pattern = re.compile(r"\{.*?\}")
					tag = tag_pattern.search(line.text)
					word_i = 0

					if not tag:
						# No tags found
						text_chunks.append({'tags': "", 'text': line.text})
					else:
						# First chunk without tags
						if tag.start() != 0:
							text_chunks.append({'tags': "", 'text': line.text[0:tag.start()]})

						# Searching for other tags
						while True:
							next_tag = tag_pattern.search(line.text, tag.end())
							tmp = {'tags': line.text[tag.start()+1:tag.end()-1], 'text': line.text[tag.end():(next_tag.start() if next_tag else None)], 'word_i': word_i}
							text_chunks.append(tmp)
							
							if len(re.findall(r"(.*?)(\s*)$", tmp['text'])[0][1]) > 0:
								word_i = word_i + 1

							if not next_tag:
								break
							tag = next_tag

					# Adding syls
					last_time = 0
					line.syls = []
					for text_chunk in text_chunks:
						try:
							pretags, kdur, posttags = re.findall(r"(.*?)\\[kK][of]?(\d+)(.*?)", text_chunk['tags'])[0][:]
							syl = Syllable()

							syl.word_i = text_chunk['word_i']
							
							syl.start_time = last_time
							syl.end_time = last_time + int(kdur) * 10
							syl.duration = int(kdur) * 10
							
							syl.inline_fx = ""
							syl.tags = pretags + posttags
							syl.prespace, syl.text, syl.postspace = re.findall(r"^(\s*)(.*?)(\s*)$", text_chunk['text'])[0][:]
							
							syl.prespace, syl.postspace = len(syl.prespace), len(syl.postspace)
							syl.width, syl.height = font.get_text_extents(syl.text)
							syl.ascent, syl.descent, syl.internal_leading, syl.external_leading = font.get_metrics()
							
							line.syls.append(syl)
							last_time = syl.end_time
						except IndexError:
							line.syls.clear()
							break

					# Calculate syllables positions with all syllables data already available
					if len(line.syls) > 0 and self.meta.play_res_x > 0 and self.meta.play_res_y > 0:
						if line.styleref.alignment > 6 or line.styleref.alignment < 4 or not vertical_kanji:
							cur_x = line.left
							for syl in line.syls:
								cur_x = cur_x + syl.prespace * space_width
								# Horizontal position
								syl.left = cur_x
								syl.center = syl.left + syl.width / 2
								syl.right = syl.left + syl.width

								if (line.styleref.alignment-1) % 3 == 0:
									syl.x = syl.left
								elif (line.styleref.alignment-2) % 3 == 0:
									syl.x = syl.center
								else:
									syl.x = syl.right
								
								cur_x = cur_x + syl.width + syl.postspace * space_width
								
								# Vertical position
								syl.top = line.top
								syl.middle = line.middle
								syl.bottom = line.bottom
								syl.y = line.y

						else: # Kanji vertical position
							max_width, sum_height = 0, 0
							for syl in line.syls:
								max_width = max(max_width, syl.width)
								sum_height = sum_height + syl.height
							
							cur_y = self.meta.play_res_y / 2 - sum_height / 2

							# Fixing line positions
							line.top = cur_y
							line.middle = self.meta.play_res_y / 2
							line.bottom = line.top + sum_height
							line.width = max_width
							line.height = sum_height
							if line.styleref.alignment == 4:
								line.center = line.left + max_width / 2
								line.right = line.left + max_width
							elif line.styleref.alignment == 5:
								line.left = line.center - max_width / 2
								line.right = line.left + max_width
							else:
								line.left = line.right - max_width
								line.center = line.left + max_width / 2

							for syl in line.syls:
								# Horizontal position
								x_fix = (max_width - syl.width) / 2
								if line.styleref.alignment == 4:
									syl.left = line.left + x_fix
									syl.center = syl.left + syl.width / 2
									syl.right = syl.left + syl.width
									syl.x = syl.left
								elif line.styleref.alignment == 5:
									syl.left = line.center - syl.width / 2
									syl.center = syl.left + syl.width / 2
									syl.right = syl.left + syl.width
									syl.x = syl.center
								else:
									syl.left = line.right - syl.width - x_fix
									syl.center = syl.left + syl.width / 2
									syl.right = syl.left + syl.width
									syl.x = syl.right

								# Vertical position
								syl.top = cur_y
								syl.middle = syl.top + syl.height / 2
								syl.bottom = syl.top + syl.height
								syl.y = syl.middle
								cur_y = cur_y + syl.height

					# Adding chars
					line.chars = []

					# Creating some local variables to avoid some useless iterations during the additions of some fields in char obj
					word_index = 0
					syl_index = 0
					char_index = 0

					tmp = ""
					if line.words:
						tmp = line.words[0]
					if line.syls:
						tmp = line.syls[0]

					# Getting chars
					for char_i, char_text in enumerate(list(line.text_stripped)):
						char = Char()

						char.start_time = line.start_time
						char.end_time = line.end_time
						char.duration = line.duration

						char.text = char_text

						# Adding indexes
						if line.syls:
							if char_index >= len("{}{}{}".format(" "*tmp.prespace, tmp.text, " "*tmp.postspace)):
								char_index = 0
								syl_index += 1
								tmp = line.syls[syl_index]

							char.word_i = tmp.word_i
							char.syl_i = syl_index
							char.syl_char_i = char_index
						else: # We have no syls, let's only work with words
							if char_index >= len("{}{}{}".format(" "*tmp.prespace, tmp.text, " "*tmp.postspace)):
								char_index = 0
								word_index += 1
								tmp = line.words[syl_index]

							char.word_i = word_index

						# Adding last fields based on the existance of syls or not
						char.start_time = tmp.start_time
						char.end_time = tmp.end_time
						char.duration = tmp.duration

						char.width, char.height = font.get_text_extents(char.text)
						char.ascent, char.descent, char.internal_leading, char.external_leading = font.get_metrics()
						
						line.chars.append(char)
						char_index += 1

					# Calculate character positions with all characters data already available
					if len(line.chars) > 0 and self.meta.play_res_x > 0 and self.meta.play_res_y > 0:
						if line.styleref.alignment > 6 or line.styleref.alignment < 4:
							cur_x = line.left
							for char in line.chars:
								# Horizontal position
								char.left = cur_x
								char.center = char.left + char.width / 2
								char.right = char.left + char.width
								
								if (line.styleref.alignment-1) % 3 == 0:
									char.x = char.left
								elif (line.styleref.alignment-2) % 3 == 0:
									char.x = char.center
								else:
									char.x = char.right
								
								cur_x = cur_x + char.width
								
								# Vertical position
								char.top = line.top
								char.middle = line.middle
								char.bottom = line.bottom
								char.y = line.y
						else:
							max_width, sum_height = 0, 0
							for char in line.chars:
								max_width = max(max_width, char.width)
								sum_height = sum_height + char.height

							cur_y = x_fix = self.meta.play_res_y / 2 - sum_height / 2
							for char in line.chars:
								# Horizontal position
								x_fix = (max_width - char.width) / 2
								if line.styleref.alignment == 4:
									char.left = line.left + x_fix
									char.center = char.left + char.width / 2
									char.right = char.left + char.width
									char.x = char.left
								elif line.styleref.alignment == 5:
									char.left = self.meta.play_res_x / 2 - char.width / 2
									char.center = char.left + char.width / 2
									char.right = char.left + char.width
									char.x = char.center
								else:
									char.left = line.right - char.width - x_fix
									char.center = char.left + char.width / 2
									char.right = char.left + char.width
									char.x = char.right

								# Vertical position
								char.top = cur_y
								char.middle = char.top + char.height / 2
								char.bottom = char.top + char.height
								char.y = char.middle
								cur_y = cur_y + char.height
		
			# Add durations between dialogs
			for style in lines_by_styles:
				lines_by_styles[style].sort(key=lambda x: x.start_time)
				for li, line in enumerate(lines_by_styles[style]):
					line.leadin = 1000.1 if li == 0 else line.start_time - lines_by_styles[style][li-1].end_time
					line.leadout =  1000.1 if li == len(lines_by_styles[style])-1 else lines_by_styles[style][li+1].start_time - line.end_time

		# Done

	def get_data(self):
		"""Utility function to retrieve easily meta styles and lines.
	
		Returns:
			:attr:`meta`, :attr:`styles` and :attr:`lines`
		"""
		return self.meta, self.styles, self.lines

	def write_line(self, line):
		"""Appends a line to the output list (which is private).
		
		Use it whenever you've prepared a line, it will not impact performance since you 
		will not actually write anything until :func:`save` will be called.

		Parameters:
			line (:class:`Line`): A line object. If not valid, TypeError is raised.
		"""
		if isinstance(line, Line):
			self.__output.append("\n%s: %d,%s,%s,%s,%s,%04d,%04d,%04d,%s,%s" % (
				"Comment" if line.comment else "Dialogue",
				line.layer,
				Convert.time(int(line.start_time)),
				Convert.time(int(line.end_time)),
				line.style,
				line.actor,
				line.margin_l,
				line.margin_r,
				line.margin_v,
				line.effect,
				line.text
			))
			self.__plines += 1
		else:
			raise TypeError("Expected Line object, got %s." % type(line)) 

	def save(self, quiet=False):
		"""Write everything inside the output list to a file.

		This should be the last function called inside your fx.py file.
		Additionally, if pyonfx.Settings.aegisub is True, then the file will automatically
		be opened with Aegisub at the end of the generation.

		Parameters:
			quiet (bool): If True, you will not get printed any message.
		"""

		# Writing to file
		with open(self.path_output, 'w', encoding="utf-8-sig") as f:
			f.writelines(self.__output)
		if not quiet:
			print("Produced lines: %d\nProcess duration (in seconds): %.3f" % (self.__plines, time.time() - self.__ptime))
		
		# Open with Aegisub?
		if Settings.aegisub:
			os.startfile(self.path_output)
