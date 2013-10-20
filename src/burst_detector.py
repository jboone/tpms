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

# Burst detection

import math

from gnuradio import gr

import numpy
import scipy.signal
import pyfftw

# http://gnuradio.org/redmine/projects/gnuradio/wiki/BlocksCodingGuide

class burst_detector(gr.basic_block):
	def __init__(self):
		super(burst_detector, self).__init__(
			name="Burst Detector",
			in_sig=[numpy.complex64],
			out_sig=[numpy.complex64]
		)

		self._burst_tag_symbol = gr.pmt.string_to_symbol('burst')
		self._burst = False

		self.block_size = 256
		
		self.hysteresis_timeout = 3 #int(math.ceil(768 / self.block_size))
		self.hysteresis_count = 0

		self.fft_window = scipy.signal.hanning(self.block_size)
		self.fft_in = pyfftw.n_byte_align_empty((self.block_size,), self.block_size, dtype='complex64')
		self.fft_out = pyfftw.n_byte_align_empty((self.block_size,), self.block_size, dtype='complex64')
		self.fft = pyfftw.FFTW(self.fft_in, self.fft_out)

	def forecast(self, noutput_items, ninput_items_required):
		block_count = int(math.ceil(float(noutput_items) / self.block_size))
		ninput_items_required[0] = block_count * self.block_size
		#print('for %d items, require %d' % (noutput_items, ninput_items_required[0]))

	def general_work(self, input_items, output_items):
		input_item = input_items[0]
		
		samples_to_consume = min(len(input_items[0]), len(output_items[0]))
		block_count = int(math.floor(samples_to_consume / self.block_size))
		samples_to_consume = block_count * self.block_size

		nitems_written = self.nitems_written(0)
		for block_n in range(block_count):
			index_start = block_n * self.block_size
			index_end = index_start + self.block_size
			block = input_item[index_start:index_end]
			#block_spectrum = numpy.fft.fft(block)
			self.fft_in[:] = block * self.fft_window
			self.fft()
			block_spectrum = self.fft_out
			block_abs = numpy.abs(block_spectrum)
			block_max = max(block_abs)
			block_sum = numpy.sum(block_abs)
			block_avg = block_sum / self.block_size
			block_spread = block_max / block_avg
			#graph = '*' * int(round(block_spread))
			#print('%.1f %s' % (block_spread, graph))
			
			if block_spread >= 10:
				self.hysteresis_count = self.hysteresis_timeout
			elif block_spread < 5:
				self.hysteresis_count -= 1
				
			#if block_max >= self.threshold_rise:
			#	self.hysteresis_count = self.hysteresis_timeout
			#elif block_max <= self.threshold_fall:
			#	self.hysteresis_count -= 1
			
			if self.hysteresis_count > 0:
				if self._burst == False:
					#print('T: %d, %d' % (nitems_written + index_start - self.block_size, nitems_written))
					self.add_item_tag(0, nitems_written + index_start - self.block_size, self._burst_tag_symbol, gr.pmt.PMT_T)
					self._burst = True
				#print('%6d %.3f' % (datetime.datetime.now().microsecond, block_max))
			else:
				if self._burst == True:
					#print('F: %d, %d' % (nitems_written + index_start, nitems_written))
					self.add_item_tag(0, nitems_written + index_start, self._burst_tag_symbol, gr.pmt.PMT_F)
					self._burst = False

		output_items[0][:samples_to_consume] = input_items[0][:samples_to_consume]

		self.consume_each(samples_to_consume)

		return samples_to_consume
