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

from gnuradio import blocks
from gnuradio import digital
from gnuradio import eng_notation
from gnuradio import filter
from gnuradio import gr

from argparse import ArgumentParser

import numpy
import sys
import math
import os
import os.path
import glob
import datetime
from iso8601 import iso8601

from collections import defaultdict

from packet import Packetizer, packet_format, packet_classify
from numpy_block import *

class FSKDemodulator(gr.top_block):
	def __init__(self, source_data, sampling_rate, carrier_hz, symbol_rate, deviation, access_code):
		super(FSKDemodulator, self).__init__()

		self._decoded = {}

		self._carrier_hz = carrier_hz
		self._deviation = deviation
		self._access_code = access_code

		samp_rate = sampling_rate
		#symbol_rate = 9920
		self.samples_per_symbol = float(samp_rate) / symbol_rate

		omega = self.samples_per_symbol * 1.0
		mu = 0.0
		gain_mu = 0.2
		gain_omega = 0.25 * gain_mu * gain_mu
		omega_relative_limit = 0.001

		tap_count = int(math.floor(self.samples_per_symbol))

		hz_n = (carrier_hz - deviation)
		taps_n = numpy.exp(numpy.arange(tap_count, dtype=numpy.float32) * 2.0j * numpy.pi * hz_n / samp_rate)
		hz_p = (carrier_hz + deviation)
		taps_p = numpy.exp(numpy.arange(tap_count, dtype=numpy.float32) * 2.0j * numpy.pi * hz_p / samp_rate)

		#source = blocks.file_source(gr.sizeof_gr_complex*1, filepath_in, False)
		# Concatenate data to compensate for correlate_access_code_bb latency
		source_data_padding_count = int(math.ceil(self.samples_per_symbol * 64))
		source_data = numpy.concatenate((source_data, numpy.zeros((source_data_padding_count,), dtype=numpy.complex64)))
		source = NumpySource(source_data)

		filter_n = filter.fir_filter_ccc(1, taps_n.tolist())
		self.connect(source, filter_n)
		filter_p = filter.fir_filter_ccc(1, taps_p.tolist())
		self.connect(source, filter_p)

		mag_n = blocks.complex_to_mag(1)
		self.connect(filter_n, mag_n)
		mag_p = blocks.complex_to_mag(1)
		self.connect(filter_p, mag_p)

		sub_pn = blocks.sub_ff()
		self.connect(mag_p, (sub_pn, 0))
		self.connect(mag_n, (sub_pn, 1))

		clock_recovery = digital.clock_recovery_mm_ff(omega, gain_omega, mu, gain_mu, omega_relative_limit)
		self.connect(sub_pn, clock_recovery)

		slicer = digital.binary_slicer_fb()
		self.connect(clock_recovery, slicer)

		access_code_correlator = digital.correlate_access_code_bb(access_code, 0)
		self.connect(slicer, access_code_correlator)

		self.packetizer = Packetizer()
		self.connect(access_code_correlator, self.packetizer)

		# sink_n = blocks.file_sink(gr.sizeof_float*1, 'out_n.rfile')
		# self.connect(mag_n, sink_n)
		# sink_p = blocks.file_sink(gr.sizeof_float*1, 'out_p.rfile')
		# self.connect(mag_p, sink_p)
		# sink_diff = blocks.file_sink(gr.sizeof_float*1, 'out_diff.rfile')
		# self.connect(sub_pn, sink_diff)
		# sink_sync = blocks.file_sink(gr.sizeof_float*1, 'out_sync.rfile')
		# self.connect(clock_recovery, sink_sync)
		# sink_slicer = blocks.file_sink(gr.sizeof_char*1, 'out_slicer.u8')
		# self.connect(slicer, sink_slicer)
		# sink_correlator = blocks.file_sink(gr.sizeof_char*1, 'out_correlator.u8')
		# self.connect(access_code_correlator, sink_correlator)

	@property
	def packets(self):
		results = []
		data = self.packetizer.data
		#print('P %s' % ''.join(map(str, data)))
		for i in range(len(data)):
			symbol = data[i]
			if symbol & 2:
				if len(data[i:]) >= 64:
					access_code_n = i - len(self._access_code)
					result = (
						data[access_code_n:i] & 1,
						data[i:] & 1,
					)
					results.append(result)
		return results[-1:]

def demodulate_ask(packet_info, source_data):
	return False

def demodulate_fsk(packet_info, source_data):
	symbol_rate = packet_info['symbol_rate']
	access_code = packet_info['preamble']
	carrier_hz = packet_info['carrier']
	deviation = packet_info['deviation']

	demodulator = FSKDemodulator(source_data, sampling_rate, carrier_hz, symbol_rate, deviation, access_code)
	demodulator.run()

	packets = demodulator.packets
	results = []
	for actual_access_code, data in packets:
		results.append({
			'decoder': 'raw',
			'data': ''.join(map(str, data)),
			'carrier': carrier_hz,
			'modulation': 'fsk',
			'symbol_rate': symbol_rate,
			'deviation': deviation,
			'access_code': access_code,
			'actual_access_code': ''.join(map(str, actual_access_code)),
		})

	return results

if __name__ == '__main__':
	parser = ArgumentParser()
	parser.add_argument('burst_directory', nargs='+', type=str)
	parser.add_argument('-r', '--rate', type=float, help="Sampling rate of data files")
	parser.add_argument('-m', '--modulation', type=str, default='fsk', help="Modulation type (fsk")
	parser.add_argument('-c', '--carrier', type=float, help="Carrier frequency within data files")
	parser.add_argument('-d', '--deviation', type=float, help="Frequency deviation")
	parser.add_argument('-p', '--preamble', type=str, help="Packet preamble or access code")
	parser.add_argument('-s', '--symbol-rate', type=float, help="Symbol rate")
	args = parser.parse_args()

	sampling_rate = args.rate

	for data_path in args.burst_directory:
		path_glob = os.path.join(data_path, '*.dat')
		files = glob.glob(path_glob)

		start_timestamp_path = os.path.join(data_path, 'timestamp.txt')
		start_timestamp = open(start_timestamp_path).read()
		start_timestamp = iso8601.parse_date(start_timestamp)

		for path in files:
			head, tail = os.path.split(path)
			filename = tail

			offset_seconds = filename.split('_')[2]
			offset_seconds = float(offset_seconds.split('.dat')[0])
			burst_timestamp = start_timestamp + iso8601.timedelta(seconds=offset_seconds)

			source_data = numpy.fromfile(path, dtype=numpy.complex64)
			#packet_info = packet_classify(source_data, sampling_rate)

			packet_info = {
				'modulation': args.modulation.lower(),
				'carrier': args.carrier,
				'deviation': args.deviation,
				'symbol_rate': args.symbol_rate,
				'preamble': args.preamble,
			}

			results = []
			if packet_info['modulation'] == 'ask':
				results = demodulate_ask(packet_info, source_data)
			elif packet_info['modulation'] == 'fsk':
				results = demodulate_fsk(packet_info, source_data)
			else:
				continue

			for result in results:
				data = result['data']

				print('%s %s %s %s %d %d %d %s' % (
					burst_timestamp.isoformat(),
					result['access_code'],
					data,
					result['modulation'],
					result['carrier'],
					result['deviation'],
					result['symbol_rate'],
					filename,
				))

	# from pylab import *

	# diff = numpy.fromfile('out_diff.rfile', dtype=numpy.float32)
	# x_diff = numpy.arange(len(diff))
	# plot(x_diff, diff)

	# sync = numpy.fromfile('out_sync.rfile', dtype=numpy.float32)
	# x_sync = numpy.arange(len(sync)) * tb.samples_per_symbol
	# plot(x_sync, sync)

	# slicer = numpy.fromfile('out_slicer.u8', dtype=numpy.uint8)
	# x_slicer = numpy.arange(len(slicer)) #* tb.samples_per_symbol
	# plot(x_slicer, slicer)

	# correlator = numpy.fromfile('out_correlator.u8', dtype=numpy.uint8)
	# x_correlator = numpy.arange(len(correlator)) #* tb.samples_per_symbol
	# plot(x_correlator, correlator)
	
	# show()
