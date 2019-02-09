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
"""
This file contains the Font class definition, which has some functions
to help getting informations from a specific font
"""
import sys

if sys.platform == "win32":
	import win32gui
	import win32ui
	import win32con

# CONFIGURATION
FONT_PRECISION = 64	# Font scale for better precision output from native font system

class Font:
	"""
	Font class definition
	"""
	def __init__(self, style):
		self.family = style.fontname
		self.bold = style.bold
		self.italic = style.italic
		self.underline = style.underline
		self.strikeout = style.strikeout
		self.size = style.fontsize
		self.xscale = style.scale_x / 100
		self.yscale = style.scale_y / 100
		self.hspace = style.spacing
		self.upscale = FONT_PRECISION
		self.downscale = 1 / FONT_PRECISION

		if sys.platform == "win32":
			# Create device context
			self.dc = win32gui.CreateCompatibleDC(None)
			# Set context coordinates mapping mode
			win32gui.SetMapMode(self.dc, win32con.MM_TEXT)
			# Set context backgrounds to transparent
			win32gui.SetBkMode(self.dc, win32con.TRANSPARENT)
			# Create font handle
			font_spec = {
				'height': int(self.size * self.upscale),
				'width': 0,
				'escapement': 0,
				'orientation': 0,
				'weight': win32con.FW_BOLD if self.bold else win32con.FW_NORMAL,
				'italic': int(self.italic),
				'underline': int(self.underline),
				'strike out': int(self.strikeout),
				'charset': win32con.DEFAULT_CHARSET,
				'out precision': win32con.OUT_TT_PRECIS,
				'clip precision': win32con.CLIP_DEFAULT_PRECIS,
				'quality': win32con.ANTIALIASED_QUALITY,
				'pitch and family': win32con.DEFAULT_PITCH + win32con.FF_DONTCARE,
				'name': self.family
			}
			font = win32ui.CreateFont(font_spec)
			win32gui.SelectObject(self.dc, font.GetSafeHandle())
		else:
			raise NotImplementedError

	def get_metrics(self):
		if sys.platform == "win32":
			metrics = win32gui.GetTextMetrics(self.dc)

			return (
				#'height': metrics['Height'] * self.downscale * self.yscale,
				metrics['Ascent'] * self.downscale * self.yscale,
				metrics['Descent'] * self.downscale * self.yscale,
				metrics['InternalLeading'] * self.downscale * self.yscale,
				metrics['ExternalLeading'] * self.downscale * self.yscale
			)
		else:
			raise NotImplementedError

	def get_text_extents(self, text):
		if sys.platform == "win32":
			cx, cy = win32gui.GetTextExtentPoint32(self.dc, text)

			return (
				(cx * self.downscale + self.hspace) * self.xscale,
				cy * self.downscale * self.yscale
			)
		else:
			raise NotImplementedError