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

import re
import math
from .font_utility import Font
from .shape import Shape

class Convert:
	"""
	This class is a collection of static methods that will help
	the user to convert everything needed to the ASS format.
	"""

	@staticmethod
	def time(ass_ms):
		"""Converts between milliseconds and ASS timestamp.

		You can probably ignore that function, you will not make use of it for KFX or typesetting generation.

		Parameters:
			ass_ms (either int or str): If int, than milliseconds are expected, else ASS timestamp as str is expected.

		Returns:
			If milliseconds -> ASS timestamp, else if ASS timestamp -> milliseconds, else ValueError will be raised.
		"""
		# Milliseconds?
		if type(ass_ms) is int and ass_ms >= 0:
			return "{:d}:{:02d}:{:02d}.{:02d}".format(
				math.floor(ass_ms / 3600000) % 10,
				math.floor(ass_ms % 3600000 / 60000),
				math.floor(ass_ms % 60000 / 1000),
				math.floor(ass_ms % 1000 / 10))
		# ASS timestamp?
		elif type(ass_ms) is str and re.match(r"^\d:\d+:\d+\.\d+$", ass_ms):
			return int(ass_ms[0]) * 3600000 + int(ass_ms[2:4]) * 60000 + int(ass_ms[5:7]) * 1000 + int(ass_ms[8:10]) * 10
		else:
			raise ValueError("Milliseconds or ASS timestamp expected")

	@staticmethod
	def coloralpha(ass_r_a, g="", b="", a=""):
		"""Converts between rgb color &/+ alpha numeric and ASS color &/+ alpha.
		
		Parameters:
			ass_r_a (int or str): If str, an ASS color + optionally alpha or only alpha is expected, else if it is a number this will be the red value or the alpha value in rgb.
			g (int, optional): If given, an rgb + optional alpha is expected, so you will have to fill also the other parameters. 
			b (int, optional): If given, an rgb + optional alpha is expected, so you will have to fill also the other parameters.
			a (int, optional): If given, an rgb + alpha is expected, so you will have to fill also the other parameters.
		
		Returns:
			According to the parameters, either an rgb + optionally alpha as multiple returns value or a str containing either an ASS color+alpha, an ASS color or an ASS alpha.
		
		Examples:
			..  code-block:: python3
				
				print( Convert.coloralpha(0) )
				print( Convert.coloralpha("&HFF&") + "\\n" )

				print( Convert.coloralpha("&H0000FF&") )
				print( Convert.coloralpha(255, 0, 0) + "\\n" )

			>>> &HFF&
			>>> 0
			>>> 
			>>> (255, 0, 0)
			>>> &H0000FF&
		"""
		# Alpha / red numeric?
		if (type(ass_r_a) == int or type(ass_r_a) == float) and ass_r_a >= 0 and ass_r_a <= 255:
			# Green + blue numeric?
			if (type(g) == int or type(g) == float) and g >= 0 and g <= 255 and \
			   (type(b) == int or type(b) == float) and b >= 0 and b <= 255: 	
				# Alpha numeric?
				if (type(a) == int or type(a) == float) and a >= 0 and a <= 255:
					return "&H{:02X}{:02X}{:02X}{:02X}".format(255 - int(a), int(b), int(g), int(ass_r_a))
				else:
					return "&H{:02X}{:02X}{:02X}&".format(int(b), int(g), int(ass_r_a))
			else:
				return "&H{:02X}&".format(255 - int(ass_r_a))
		# ASS value?
		elif type(ass_r_a) == str:
			# ASS alpha?
			if re.match(r"^&H[0-9a-fA-F]{2}&$", ass_r_a):
				return 255 - int(ass_r_a[2:4], 16)
			# ASS color?
			elif re.match(r"^&H[0-9a-fA-F]{6}&$", ass_r_a):
				return int(ass_r_a[6:8], 16), int(ass_r_a[4:6], 16), int(ass_r_a[2:4], 16)
			# ASS color+alpha (from style definition)?
			elif re.match(r"^&H[0-9a-fA-F]{8}$", ass_r_a):
				return int(ass_r_a[8:10], 16), int(ass_r_a[6:8], 16), int(ass_r_a[4:6], 16), 255 - int(ass_r_a[2:4], 16)
			else:
				raise ValueError("Invalid ASS string")
		else:
			raise ValueError("Color, Alpha, Color+Alpha as numeric or ASS expected")

	@staticmethod
	def text_to_shape(obj, fscx=None, fscy=None):
		"""Converts text with given style information to an ASS shape.

		Using this, you can easily create impressive text masks or deforming effects.
		
		Parameters:
			obj (Line, Word, Syllable or Char): An object of class Line, Word, Syllable or Char.
			fscx (float, optional): The scale_x value for the shape.
			fscy (float, optional): The scale_y value for the shape.
		
		Returns:
			A Shape object, representing the text with the style format values of the object.

		Examples:
			..  code-block:: python3
				
				line = Line.copy(lines[1])
				line.text = "{\\\\an7\\\\pos(%.3f,%.3f)\\\\p1}%s" % (line.left, line.top, convert.text_to_shape(line))
				io.write_line(line)
		"""
		# Obtaining information and editing values of style if requested
		original_scale_x = obj.styleref.scale_x
		original_scale_y = obj.styleref.scale_y
		
		# Editing temporary the style to properly get the shape
		if fscx:
			obj.styleref.scale_x = fscx
		if fscy:
			obj.styleref.scale_y = fscy

		# Obtaining font information from style and obtaining shape
		font = Font(obj.styleref)
		shape = font.text_to_shape(obj.text)
		# Clearing resources to not let overflow errors take over
		del font

		# Restoring values of style and returning the shape converted
		if fscx:
			obj.styleref.scale_x = original_scale_x
		if fscy:
			obj.styleref.scale_y = original_scale_y
		return shape

	@staticmethod
	def text_to_clip(obj, an=5, fscx=None, fscy=None):
		"""Converts text with given style information to an ASS shape, applying some translation/scaling to it since
		it is not possible to position a shape with \\pos() once it is in a clip.

		This is an high level function since it does some additional operations, check text_to_shape for further infromations.
		
		Parameters:
			obj (Line, Word, Syllable or Char): An object of class Line, Word, Syllable or Char.
			an (integer, optional): The alignment wanted for the shape.
			fscx (float, optional): The scale_x value for the shape.
			fscy (float, optional): The scale_y value for the shape.
		
		Returns:
			A Shape object, representing the text with the style format values of the object.

		Examples:
			..  code-block:: python3
				
				line = Line.copy(lines[1])
				line.text = "{\\\\an5\\\\pos(%.3f,%.3f)\\\\clip(%s)}%s" % (line.center, line.middle, convert.text_to_clip(line), line.text)
				io.write_line(line)
		"""
		# Checking for errors
		if an < 1 or an > 9:
			raise ValueError("Alignment value must be an integer between 1 and 9")

		# Setting default values
		if not fscx:
			fscx = obj.styleref.scale_x
		if not fscy:
			fscy = obj.styleref.scale_y

		# Obtaining text converted to shape
		shape = Convert.text_to_shape(obj, fscx, fscy)

		# Setting mult_x based on alignment
		if an % 3 == 1: # an=1 or an=4 or an=7
			mult_x = 0
		elif an % 3 == 2: # an=2 or an=5 or an=8
			mult_x = 1/2
		else:
			mult_x = 1

		# Setting mult_y based on alignment
		if an < 4:
			mult_y = 1
		elif an < 7:
			mult_y = 1/2
		else:
			mult_y = 0

		# Calculating offsets
		cx = obj.left - obj.width*mult_x * (fscx-obj.styleref.scale_x) / obj.styleref.scale_x
		cy = obj.top - obj.height*mult_y * (fscy-obj.styleref.scale_y) / obj.styleref.scale_y

		return shape.move(cx, cy)

	@staticmethod
	def text_to_pixels(text, style, off_x=0, off_y=0):
		pass

	@staticmethod
	def shape_to_pixels(shape):
		pass

	@staticmethod
	def image_to_ass(image):
		pass

	@staticmethod
	def image_to_pixels(image):
		pass
