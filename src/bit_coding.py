#!/usr/bin/env python

#
# Copyright 2013 Jared Boone
#
# This file is part of the TPMS project.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

# import numpy

# def copy_truncated(a, mod_n):
# 	return a[:(len(a) / mod_n) * mod_n].copy()

# def differential_manchester_decode(a):
# 	last_bit = 0
# 	a = copy_truncated(a, 2)
# 	a = a.reshape((-1, 2))
# 	result = []
# 	for pair in a:
# 		if pair[0] == pair[1]:
# 			result.append('X')
# 		elif last_bit != pair[0]:
# 			result.append('0')
# 		else:
# 			result.append('1')
# 		last_bit = pair[1]
# 	return result

# def biphase_decode(a):
# 	a = copy_truncated(a, 2)
# 	a = a.reshape((-1, 2))
# 	result = []
# 	for pair in a:
# 		if pair[0] != pair[1]:
# 			result.append('1')
# 		else:
# 			result.append('0')
# 	return result
	
# def manchester_decode(a):
# 	a = copy_truncated(a, 2)
# 	a = a.reshape((-1, 2))
# 	result = []
# 	for pair in a:
# 		if pair[0] == pair[1]:
# 			result.append('X')
# 		else:
# 			result.append(str(pair[1]))
# 	return result

def string_to_symbols(s, symbol_length):
	return [s[n:n+symbol_length] for n in range(0, len(s), symbol_length)]

def differential_manchester_decode(s):
	symbols = string_to_symbols(s, 2)
	last_bit = '0'
	result = []
	for symbol in symbols:
		if len(symbol) == 2:
			if symbol[0] == symbol[1]:
				result.append('X')
			elif last_bit != symbol[0]:
				result.append('0')
			else:
				result.append('1')
			last_bit = symbol[1]
		else:
			result.append('X')
	return ''.join(result)

def manchester_decode(s):
	symbols = string_to_symbols(s, 2)
	result = []
	for symbol in symbols:
		if len(symbol) == 2:
			if symbol[0] == symbol[1]:
				result.append('X')
			else:
				result.append(symbol[1])
		else:
			result.append('X')
	return ''.join(result)