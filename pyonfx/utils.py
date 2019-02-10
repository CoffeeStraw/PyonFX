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

import math
from .convert import Convert

class Utils:
	"""
	This class is a collection of static methods that will help the user in some tasks.
	"""

	@staticmethod
	def all_non_empty(lines_chars_syls_or_words):
		"""
		Helps to not check everytime for text containing only spaces or object's duration equals to zero.

		Parameters:
			lines_chars_syls_or_words (list of :class:`Line<pyonfx.ass_utility.Line>`, :class:`Char<pyonfx.ass_utility.Char>`, :class:`Syllable<pyonfx.ass_utility.Syllable>` or :class:`Word<pyonfx.ass_utility.Word>`)

		Returns:
			An enumerate object containing lines_chars_syls_or_words without objects with duration equals to zero or without some text except spaces.
		"""
		out = []
		for obj in lines_chars_syls_or_words:
			if obj.text.strip() and obj.duration > 0:
				out.append(obj) 
		return enumerate(out)

	@staticmethod
	def clean_tags(text):
		# TODO: Cleans up ASS subtitle lines of badly-formed override. Returns a cleaned up text. 
		pass

	@staticmethod
	def accelerate(pct, accelerator):
		# Modifies pct according to the acceleration provided.
		# TO DO: Implement acceleration based on bezier's curve
		return pct^accelerator

	@staticmethod
	def interpolate(pct, val1, val2, acc=1.0):
		"""
		| Interpolates 2 given values (ASS colors, ASS alpha channels or numbers) by percent value as decimal number.
		| You can also provide a http://cubic-bezier.com to accelerate based on bezier curves. (TO DO)
		|
		| You could use that for the calculation of color/alpha gradients.

		Parameters:
			pct (float): Percent value of the interpolation.
			val1 (int, float or str): First value to interpolate (either string or number).
			val2 (int, float or str): Second value to interpolate (either string or number).
			acc (float, optional): Optional acceleration that influences final percent value.
		
		Returns:
			Interpolated value of given 2 values (so either a string or a number).

		Examples:
			..  code-block:: python3

				print( Utils.interpolate(0.5, 10, 20) )
				print( Utils.interpolate(0.9, "&HFFFFFF&", "&H000000&") )

			>>> 15
			>>> &HE5E5E5&
		"""
		if pct > 1.0 or pct < 0:
			raise ValueError("Percent value must be a float between 0.0 and 1.0, but your was " + str(pct))
		
		# Calculating acceleration (if requested)
		pct = Utils.accelerate(pct, acc) if acc != 1.0 else pct

		# Interpolating
		if type(val1) is str and type(val2) is str:
			val1 = Convert.coloralpha(val1)
			val2 = Convert.coloralpha(val2)

			if type(val1) == tuple and type(val2) == tuple:
				len_v1 = len(val1)
				len_v2 = len(val2)

				if len_v1 != len_v2:
					raise TypeError("ASS values must have the same type (either two alphas, two colors or two colors+alpha)")
				elif len_v1 == 3 and len_v2 == 3: # Color
					r = int(val1[0] + (val2[0] - val1[0]) * pct)
					g = int(val1[1] + (val2[1] - val1[1]) * pct)
					b = int(val1[2] + (val2[2] - val1[2]) * pct)
					return Convert.coloralpha(r, g, b)
				else: # Color+alpha
					r = int(val1[0] + (val2[0] - val1[0]) * pct)
					g = int(val1[1] + (val2[1] - val1[1]) * pct)
					b = int(val1[2] + (val2[2] - val1[2]) * pct)
					a = int(val1[3] + (val2[3] - val1[3]) * pct)
					return Convert.coloralpha(r, g, b, a)
			elif type(val1) == int and type(val2) == int: # Alpha
				a = int(val1 + (val2 - val1) * pct)
				return Convert.coloralpha(a)
		elif (type(val1) is float and type(val2) is float) or \
			 (type(val1) is int   and type(val2) is float) or \
			 (type(val1) is float and type(val2) is int)   or \
			 (type(val1) is int   and type(val2) is int):
			return val1 + (val2 - val1) * pct
		else:
			raise TypeError("Invalid parameter(s) type, either pass two strings or two numbers")


class FrameUtility:
	"""
	This class helps in the stressfull calculation of frames per frame.

	Parameters:
		start_time (positive float): Initial time
		end_time (positive float): Final time
		fr (positive float, optional): Frame Duration

	Returns:
		Returns a Generator containing start_time, end_time, index and total number of frames for each step.
	
	Examples:
		..  code-block:: python3
			:emphasize-lines: 1

			FU = FrameUtility(0, 100)
			for s, e, i, n in FU:
				print(f"Frame {i}/{n}: {s} - {e}")

		>>> Frame 1/3: 0 - 41.71
		>>> Frame 2/3: 41.71 - 83.42
		>>> Frame 3/3: 83.42 - 100

	"""
	def __init__(self, start_time, end_time, fr=41.71):
		# Checking for invalid values
		if start_time < 0 or end_time < 0 or fr <= 0 or end_time < start_time:
			raise ValueError("Positive values and/or end_time > start_time expected.")

		# Calculating number of frames
		self.n = math.ceil((end_time - start_time)/fr)

		# Defining fields
		self.start_time = start_time
		self.end_time = end_time
		self.current_time = fr
		self.fr = fr

	def __iter__(self):
		# For loop for the first n-1 frames
		for i in range(1, self.n):
			yield (round(self.start_time, 2), round(self.start_time + self.fr, 2), i, self.n)
			self.start_time += self.fr
			self.current_time += self.fr

		# Last frame, with end value clamped at end_time
		yield (round(self.start_time, 2), round(self.end_time, 2), self.n, self.n)

		# Resetting to make this object usable again
		self.start_time = self.start_time - self.fr*max(self.n-1, 0)
		self.current_time = self.fr

	def add(self, start_time, end_time, end_value, accelerator=1.0):
		"""
		| This function makes a lot easier the calculation of tags value.
		| You can see this as a \"\\t\" tag usable in frame per frame operations.
		| Use it in a for loop which iterates a FrameUtility object, as you can see in the example.

		Examples:
			..  code-block:: python3
				:emphasize-lines: 4,5
				
				FU = FrameUtility(0, 105, 40)
				for s, e, i, n in FU:
					fsc = 100
					fsc += FU.add(0, 50, 50)
					fsc += FU.add(50, 100, -50)
					print(f"Frame {i}/{n}: {s} - {e}; fsc: {fsc}")

			>>> Frame 1/3: 0 - 40; fsc: 140.0
			>>> Frame 2/3: 40 - 80; fsc: 120.0
			>>> Frame 3/3: 80 - 105; fsc: 100
		"""

		if self.current_time < start_time:
			return 0
		elif self.current_time > end_time:
			return end_value

		pstart = self.current_time - start_time
		pend = end_time - start_time
		return Utils.interpolate(pstart/pend, 0, end_value, accelerator)