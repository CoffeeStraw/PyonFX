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

class Convert:
	"""
	This class is a collection of static methods that will help
	the user toconvert everything needed to the ASS format.
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
		if type(ass_r_a) == int and ass_r_a >= 0 and ass_r_a <= 255:
			# Green + blue numeric?
			if type(g) == int and g >= 0 and g <= 255 and type(b) == int and b >= 0 and b <= 255: 	
				# Alpha numeric?
				if type(a) == int and a >= 0 and a <= 255:
					return "&H{:02X}{:02X}{:02X}{:02X}".format(255 - a, b, g, ass_r_a)
				else:
					return "&H{:02X}{:02X}{:02X}&".format(b, g, ass_r_a)
			else:
				return "&H{:02X}&".format(255 - ass_r_a)
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
	def shape_to_pixels(shape):
		pass

	@staticmethod
	def text_to_shape(text, style):
		pass

	@staticmethod
	def text_to_pixels(text, style, off_x=0, off_y=0):
		pass

	@staticmethod
	def image_to_ass(image):
		pass

	@staticmethod
	def image_to_pixels(image):
		pass
