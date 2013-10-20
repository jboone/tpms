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

from gnuradio import gr

import numpy

class NumpySource(gr.sync_block):
	def __init__(self, data):
		super(NumpySource, self).__init__("NumpySource", None, [data.dtype])
		self._data = data

	def work(self, input_items, output_items):
		if len(self._data) == 0:
			return -1

		noutput_items = min(len(output_items[0]), len(self._data))
		#print('source %s' % noutput_items)
		output_items[0][:noutput_items] = self._data[:noutput_items]
		self._data = self._data[noutput_items:]
		return noutput_items

class NumpySink(gr.sync_block):
	def __init__(self, dtype=None):
		super(NumpySink, self).__init__("NumpySink", [dtype], None)

		self._data = numpy.empty((0,), dtype=dtype)

	def work(self, input_items, output_items):
		noutput_items = len(input_items[0])
		if noutput_items > 0:
			#print('sink %s' % noutput_items)
			self._data = numpy.concatenate((self._data, input_items[0]))
		return noutput_items

	@property
	def data(self):
		return self._data
