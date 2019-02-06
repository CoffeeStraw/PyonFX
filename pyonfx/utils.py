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

	def clean_tags(text):
		# TODO: Cleans up ASS subtitle lines of badly-formed override. Returns a cleaned up text. 
		pass