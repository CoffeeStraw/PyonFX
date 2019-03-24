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
from inspect import signature

def shape_value_format(x, prec=3):
	# Utility function to properly format values for shapes
	return f"{x:.{prec}f}".rstrip('0').rstrip('.')


class Shape:
	"""
	This class is a collection of static methods that will help
	the user to work in a comfy way with ASS paths.
	"""
	@staticmethod
	def filter(shape, filt):
		"""Sends every point of a shape through given filter function to change them.

		Working with outline points can be used to deform the whole shape and make f.e. a wobble effect.

		Parameters:
			shape (str): The shape in ASS format as a string.
			filter (function): A function with two (or optionally three) parameters. It will define how each coordinate will be changed. The first two parameters represent the x and y coordinates of each point. The third optional it represents the type of each point (move, line, bezier...).

		Returns:
			The filtered shape as a string.

		Examples:
			..  code-block:: python3
				
				original = "m 0 0 l 20 0 20 10 0 10"
				dest = Shape.filter(original, lambda x, y: (x+10, y+5) )  # Move each point of the shape
		"""
		if type(shape) is not str or not callable(filt):
			raise TypeError("String and/or lambda function expected")

		# Getting all points and commands in a list
		cmds_and_points = shape.split()
		i = 0
		n = len(cmds_and_points)

		# Checking whether the function take the typ parameter or not
		if len(signature(filt).parameters) == 2:
			while i < n:
				try:
					# Applying filter
					x, y = filt(float(cmds_and_points[i]), float(cmds_and_points[i+1]))
				except ValueError:
					# We have found a string, let's skip this
					i += 1
					continue
				except IndexError:
					raise ValueError("Shape provided is not valid. Please check if a value is missing or if you have added an extra one at the end")

				# Convert back to string the results for later
				cmds_and_points[i:i+2] = shape_value_format(x), shape_value_format(y)
				i += 2
		else:
			typ = ""
			while i < n:
				try:
					# Applying filter
					x, y = filt(float(cmds_and_points[i]), float(cmds_and_points[i+1]), typ)
				except ValueError:
					# We have found a string, let's skip this
					typ = cmds_and_points[i]
					i += 1
					continue
				except IndexError:
					raise ValueError("Shape provided is not valid. Please check if a value is missing or if you have added an extra one at the end")

				# Convert back to string the results for later
				cmds_and_points[i:i+2] = shape_value_format(x), shape_value_format(y)
				i += 2

		# Sew up everything back
		return ' '.join(cmds_and_points)

	@staticmethod
	def bounding(shape):
		"""Calculates shape bounding box.

		You can use this to get more precise information about a shape (width, height, position).

		Parameters:
			shape (str): The shape in ASS format as a string.

		Returns:
			A tuple (x0, y0, x1, y1) containing coordinates of the bounding box.

		Examples:
			..  code-block:: python3
			
				original = "m -100.5 0 l 100 0 b 100 100 -100 100 -100.5 0 c"
				x0, y0, x1, y1 = Shape.bounding(original)
		"""
		
		# Bounding data
		x0, y0, x1, y1 = None, None, None, None

		# Calculate minimal and maximal coordinates
		def filt(x, y):
			nonlocal x0, y0, x1, y1
			if x0:
				x0, y0, x1, y1 = min(x0, x), min(y0, y), max(x1, x), max(y1, y)
			else:
				x0, y0, x1, y1 = x, y, x, y
			return x, y
		
		Shape.filter(shape, filt)
		return x0, y0, x1, y1

	@staticmethod
	def move(shape, x=None, y=None):
		"""Moves shape coordinates in given direction.

		| If neither x and y are passed, it will automatically center the shape to the origin.
		| This function is an high level function, it just uses Shape.filter, which is more advanced. Additionally, it is an easy way to center a shape.

		Parameters:
			shape (str): The shape in ASS format as a string.
			x (int or float): Displacement along the x-axis.
			y (int or float): Displacement along the y-axis.

		Returns:
			The shape moved to the new position.
		"""
		if not x and not y:
			x, y = [-el for el in Shape.bounding(shape)[0:2]]
		elif not x:
			x = 0
		elif not y:
			y = 0

		return Shape.filter(shape, lambda cx, cy: (cx+x, cy+y) )

	@staticmethod
	def flatten(shape, tolerance=1.0):
		"""Splits shape's bezier curves into lines.

		| You should use this before using shape.filter to work with more outline points for smoother deforming.
		| Additionally, it is suggested to call also shape.split, to increase the precision.

		Parameters:
			shape (str): The shape in ASS format as a string.
			tolerance (float): Angle in degree to define a curve as flat (increasing it will boost performance during reproduction, but lower accuracy)

		Returns:
			The shape as a string, with bezier curves converted to lines.
		"""
		# TO DO: Make this function iterative, recursion is bad.

		if type(shape) is not str:
			raise TypeError("String expected")

		# Inner functions definitions
		# 4th degree curve subdivider (De Casteljau)
		def curve4_subdivide(x0, y0, x1, y1, x2, y2, x3, y3, pct):
			# Calculate points on curve vectors
			x01, y01, x12, y12, x23, y23 = (x0+x1)*pct, (y0+y1)*pct, (x1+x2)*pct, (y1+y2)*pct, (x2+x3)*pct, (y2+y3)*pct
			x012, y012, x123, y123 = (x01+x12)*pct, (y01+y12)*pct, (x12+x23)*pct, (y12+y23)*pct
			x0123, y0123 = (x012+x123)*pct, (y012+y123)*pct
			# Return new 2 curves
			return x0, y0, x01, y01, x012, y012, x0123, y0123, x0123, y0123, x123, y123, x23, y23, x3, y3

		# Check flatness of 4th degree curve with angles
		def curve4_is_flat(x0, y0, x1, y1, x2, y2, x3, y3):
			# Pack curve vectors (only ones non zero)
			vecs = [[x1 - x0, y1 - y0], [x2 - x1, y2 - y1], [x3 - x2, y3 - y2]]
			vecs = [el for el in vecs if not(el[0] == 0 and el[1] == 0)]

			# Inner functions to calculate degrees between two 2d vectors
			def dotproduct(v1, v2):
				return sum((a*b) for a, b in zip(v1, v2))

			def length(v):
				return math.sqrt(dotproduct(v, v))

			def get_angle(v1, v2):
				calc = max(min(dotproduct(v1, v2) / (length(v1) * length(v2)), 1), -1) # Clamping value to prevent errors
				angle = math.degrees(math.acos(calc))
				if (v1[0]*v2[1] - v1[1]*v2[0]) < 0:
					return -angle
				return angle

			# Check flatness on vectors
			for i in range(1,len(vecs)):
				if abs(get_angle(vecs[i-1], vecs[i])) > tolerance:
					return False
			return True

		# Inner function to convert 4th degree curve to line points
		def curve4_to_lines(x0, y0, x1, y1, x2, y2, x3, y3):
			# Line points buffer
			pts = ""

			# Conversion in recursive processing
			def convert_recursive(x0, y0, x1, y1, x2, y2, x3, y3):
				if curve4_is_flat(x0, y0, x1, y1, x2, y2, x3, y3):
					nonlocal pts
					x3, y3 = shape_value_format(x3), shape_value_format(y3)
					pts += f"{x3} {y3} "
					return

				x10, y10, x11, y11, x12, y12, x13, y13, x20, y20, x21, y21, x22, y22, x23, y23 = curve4_subdivide(x0, y0, x1, y1, x2, y2, x3, y3, 0.5)
				convert_recursive(x10, y10, x11, y11, x12, y12, x13, y13)
				convert_recursive(x20, y20, x21, y21, x22, y22, x23, y23)

			# Splitting curve recursively until we're not satisfied (angle <= tolerance)
			convert_recursive(x0, y0, x1, y1, x2, y2, x3, y3)
			# Return resulting points
			return pts[:-1]

		# Getting all points and commands in a list
		cmds_and_points = shape.split()
		shape = ""
		i = 0
		n = len(cmds_and_points)

		# Scanning all commands and points
		while i < n:
			if cmds_and_points[i] == "b":  # We've found a curve, let's split it into short lines
				try:
					# Getting all the points, if we don't have exactly 8 points, shape is not valid
					x0, y0 = float(cmds_and_points[i-2]), float(cmds_and_points[i-1])
					x1, y1 = float(cmds_and_points[i+1]), float(cmds_and_points[i+2])
					x2, y2 = float(cmds_and_points[i+3]), float(cmds_and_points[i+4])
					x3, y3 = float(cmds_and_points[i+5]), float(cmds_and_points[i+6])
				except IndexError:
					raise ValueError("Shape providen is not valid (not enough points for a curve)")

				# Obtaining the converted curve and saving it for later
				cmds_and_points[i] = "l"
				cmds_and_points[i+1] = curve4_to_lines(x0, y0, x1, y1, x2, y2, x3, y3)
				
				i += 2
				n -= 3

				# Deleting the remaining points
				for unused_ in range(3):
					del cmds_and_points[i]

				# Deleting last two points only if needed
				if i+2 >= n or cmds_and_points[i+2] != "b":
					# I hate redundant code :)
					for unused_ in range(2):
						del cmds_and_points[i]
					n -= 2
			elif cmds_and_points[i] == "c": # Deleting c tag?
				del cmds_and_points[i]
				n -= 1
			else:
				i += 1
		
		return ' '.join(cmds_and_points)

	@staticmethod
	def split(shape, max_len=10):
		"""Splits shape lines into shorter segments with maximum given length.

		You can call this before using Shape.filter
		to work with more outline points for smoother deforming.

		Parameters:
			shape (str): The shape in ASS format as a string.
			max_len (int or float): The max length that you want all the line to be

		Returns:
			A new shape as string with lines splitted.
		"""
		if type(shape) is not str or type(max_len) is not int:
			raise TypeError("String and/or integer expected")
		if max_len <= 0:
			raise ValueError("The length of segments must be a positive and non-zero value")

		# Internal function to help splitting a line
		def line_split(x0, y0, x1, y1):
			x0, y0, x1, y1 = float(x0), float(y0), float(x1), float(y1)
			# Line direction & length
			rel_x, rel_y = x1 - x0, y1 - y0
			distance = math.sqrt(rel_x*rel_x + rel_y*rel_y)
			# If the line is too long -> split
			if distance > max_len:
				lines, distance_rest = [], distance % max_len
				cur_distance = distance_rest if distance_rest > 0 else max_len
				
				while cur_distance <= distance:
					pct = cur_distance / distance
					x, y = shape_value_format(x0 + rel_x * pct), shape_value_format(y0 + rel_y * pct)
					
					lines.append(f"{x} {y}")
					cur_distance += max_len
				
				return " ".join(lines), lines[-1].split()
			else: # No line split
				x1, y1 = shape_value_format(x1), shape_value_format(y1)
				return f"{x1} {y1}", [x1, y1]

		# Getting all points and commands in a list
		cmds_and_points = shape.split()
		i = 0
		n = len(cmds_and_points)
		
		# Utility variables
		is_line = False
		previous_two = None
		last_move = None

		# Splitting everything splittable, probably improvable
		while i < n:
			current = cmds_and_points[i]
			if current == 'l':
				# Activate line mode, save previous two points
				is_line = True
				if not previous_two: # If we're not running into contiguous line, we need to save the previous two
					previous_two = [cmds_and_points[i-2], cmds_and_points[i-1]]
				i += 1
			elif current == 'm' or current == 'n' or current == 'b' or current == 's' or current == 'p' or current == 'c':
				if current == 'm':
					if last_move: # If we had a previous move, we need to close the previous figure before proceding
						x0, y0 = None, None
						if previous_two: # If I don't have previous point, I can read them on cmds_and_points, else I wil take 'em
							x0, y0 = previous_two[0], previous_two[1]
						else:
							x0, y0 = cmds_and_points[i-2], cmds_and_points[i-1]

						if not(x0 == last_move[0] and y0 == last_move[1]): # Closing last figure
							cmds_and_points[i] = line_split(x0, y0, last_move[0], last_move[1])[0] + " m"
					last_move = [cmds_and_points[i+1], cmds_and_points[i+2]]

				# Disabling line mode, removing previous two points
				is_line = False
				previous_two = None
				i += 1
			elif is_line:
				# Do the work with the two points found and the previous two
				cmds_and_points[i], previous_two = line_split(previous_two[0], previous_two[1], cmds_and_points[i], cmds_and_points[i+1])
				del cmds_and_points[i+1]
				# Let's go to the next two points or tag
				i += 1
				n -= 1
			else: # We're working with points that are not lines points, let's go forward
				i += 2

		# Close last figure of new shape, taking two last points and two last points of move
		i = n
		if not previous_two:
			while i >= 0:
				current = cmds_and_points[i]
				current_prev = cmds_and_points[i-1]
				if current != 'm' and current != 'n' and current != 'b' and current != 's' and current != 'p' and current != 'c' and \
				   current_prev != 'm' and current_prev != 'n' and current_prev != 'b' and current_prev != 's' and current_prev != 'p' and current_prev != 'c':
					previous_two = [current, current_prev]
					break
				i -= 1
		if not(previous_two[0] == last_move[0] and previous_two[1] == last_move[1]): # Split!
			cmds_and_points.append("l " + line_split(previous_two[0], previous_two[1], last_move[0], last_move[1])[0])

		# Sew up everything back
		return ' '.join(cmds_and_points)

	@staticmethod
	def to_outline(shape, bord_xy, bord_y=None, mode="round"):
		#Converts shape command for filling to a shape command for stroking.

		#You could use this for border textures.

		#Parameters:
		#	shape (str): The shape in ASS format as a string.

		#Returns:
		#	A new shape as string, representing the border of the input.
		raise NotImplementedError

	@staticmethod
	def ring(out_r, in_r):
		try:
			out_r2, in_r2 = out_r*2, in_r*2
			off = out_r - in_r
			off_in_r = off + in_r
			off_in_r2 = off + in_r2
		except TypeError:
			raise TypeError("Number(s) expected")

		if in_r >= out_r:
			raise ValueError("Valid number expected. Inner radius must be less than outer radius")

		r = shape_value_format
		return "m 0 %s "\
		"b 0 %s 0 0 %s 0 "\
		"%s 0 %s 0 %s %s "\
		"%s %s %s %s %s %s "\
		"%s %s 0 %s 0 %s "\
		"m %s %s "\
		"b %s %s %s %s %s %s "\
		"%s %s %s %s %s %s "\
		"%s %s %s %s %s %s "\
		"%s %s %s %s %s %s" % (
			r(out_r),																			# outer move
			r(out_r), r(out_r),																	# outer curve 1
			r(out_r), r(out_r2), r(out_r2), r(out_r),											# outer curve 2
			r(out_r2), r(out_r), r(out_r2), r(out_r2), r(out_r), r(out_r2),						# outer curve 3
			r(out_r), r(out_r2), r(out_r2), r(out_r),											# outer curve 4
			r(off), r(off_in_r),																# inner move
			r(off), r(off_in_r), r(off), r(off_in_r2), r(off_in_r), r(off_in_r2),				# inner curve 1
			r(off_in_r), r(off_in_r2), r(off_in_r2), r(off_in_r2), r(off_in_r2), r(off_in_r),	# inner curve 2
			r(off_in_r2), r(off_in_r), r(off_in_r2), r(off), r(off_in_r), r(off),				# inner curve 3
			r(off_in_r), r(off), r(off), r(off), r(off), r(off_in_r)							# inner curve 4
		)

	@staticmethod
	def ellipse(w, h):
		"""Returns a shape command of an ellipse with given width and height.

		You could use that to create rounded stribes or arcs in combination with blurring for light effects.

		Parameters:
			w (int or float): The width for the ellipse.
			h (int or float): The height for the ellipse.
		
		Returns:
			A shape command represeting an ellipse.
		"""
		try:
			w2, h2 = w/2, h/2
		except TypeError:
			raise TypeError("Number(s) expected")

		r = shape_value_format
		return "m 0 %s "\
		"b 0 %s 0 0 %s 0 "\
		"%s 0 %s 0 %s %s "\
		"%s %s %s %s %s %s "\
		"%s %s 0 %s 0 %s" % (
			r(h2),									# move
			r(h2), r(w2),							# curve 1
			r(w2), r(w), r(w), r(h2),				# curve 2
			r(w), r(h2), r(w), r(h), r(w2), r(h),	# curve 3
			r(w2), r(h), r(h), r(h2)				# curve 4
		)

	@staticmethod
	def heart(size, offset=0):
		# Build shape from template
		try:
			mult = size / 30
		except TypeError:
			raise TypeError("Size parameter must be a number")
		shape = Shape.filter("m 15 30 b 27 22 30 18 30 14 30 8 22 0 15 10 8 0 0 8 0 14 0 18 3 22 15 30", lambda x, y: (x * mult, y * mult) )

		# Shift mid point of heart vertically
		count = 0
		def shift_mid_point(x, y):
			nonlocal count
			count += 1

			if count == 7:
				try:
					return x, y+offset
				except:
					raise TypeError("Offset parameter must be a number")		
			return x, y

		# Return result
		return Shape.filter(shape, shift_mid_point)

	@staticmethod
	def rectangle(w=1, h=1):
		"""Returns a shape command of a rectangle with given width and height.

		Remember that a rectangle with width=1 and height=1 is a pixel.

		Parameters:
			w (int or float): The width for the rectangle.
			h (int or float): The height for the rectangle.
		
		Returns:
			A shape command represeting an rectangle.
		"""
		try:
			r = shape_value_format
			return "m 0 0 l %s 0 %s %s 0 %s 0 0" % (r(w), r(w), r(h), r(h))
		except TypeError:
			raise TypeError("Number(s) expected")

	@staticmethod
	def triangle(size):
		try:
			h = math.sqrt(3) * size / 2
			base = -h / 6
		except TypeError:
			raise TypeError("Number expected")

		r = shape_value_format
		return "m %s %s l %s %s 0 %s %s %s" % (r(size/2), r(base), r(size), r(base+h), r(base+h), r(size/2), r(base))
