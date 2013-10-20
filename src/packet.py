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

import math
import numpy

def packet_format(l):
	if 'X' in l:
		return None
	else:
		return ''.join(map(str, l))

def packet_print(l):
	formatted = packet_format(l)
	if formatted is not None:
		print(formatted)

class Packetizer(gr.sync_block):
	def __init__(self):
		super(Packetizer, self).__init__(
			"Packetizer",
			[numpy.uint8],
			None
		)
		self._data = None

	@property
	def data(self):
		return self._data

	def work(self, input_items, output_items):
		nitems = len(input_items[0])
		
		if self._data is None:
			self._data = input_items[0].copy()
		else:
			self._data = numpy.concatenate((self._data, input_items[0]))
			
		return len(input_items[0])





def blank_array_range(data, center, deviation):
	low_n = max(center - deviation, 0)
	high_n = min(center + deviation, len(data))
	data[low_n:high_n] = 0



from matplotlib import pyplot
import scipy.stats
import scipy.signal




def packet_classify(data, sampling_rate):
	# From "Automatic Modulation Recognition of Communication Signals"
	#
	# a = numpy.absolute(data)
	# m_a = sum(a) / len(data)
	# #print('m_a', m_a)
	# a_n = a / m_a
	# a_cn = a_n - 1.0
	# a_cn_dft = numpy.absolute(numpy.fft.fftshift(numpy.fft.fft(a_cn)))
	# gamma_max = numpy.max(numpy.power(a_cn_dft, 2.0))
	# t_gamma_max = 10000
	# if gamma_max < t_gamma_max:
	# 	modulation_alt = 'fsk'
	# else:
	# 	modulation_alt = 'ask'
	# a_t = 0.5

	# From "Fuzzy logic classifier for radio signals recognition"
	#
	# envelope = a
	# k1 = scipy.stats.kurtosis(envelope, fisher=False, bias=False)
	# print(k1)

	windowed_samples = data * scipy.signal.hanning(len(data))
	spectrum = numpy.fft.fftshift(numpy.fft.fft(windowed_samples))
	spectrum_mag = numpy.absolute(spectrum)
	# spectrum_mag_sum = sum(spectrum_mag)
	# spectrum_mag_avg = spectrum_mag_sum / len(spectrum_mag)

	def arg_hz(n):
		return ((n / float(len(spectrum_mag))) - 0.5) * sampling_rate

	mute_offset_hz = 2e3
	mute_offset_n = int(math.ceil(float(mute_offset_hz) / sampling_rate * len(spectrum_mag)))
	
	peak1_n = numpy.argmax(spectrum_mag)
	peak1_hz = arg_hz(peak1_n)
	peak1_mag = spectrum_mag[peak1_n]
	#print('peak 1: %s %s' % (peak1_hz, peak1_mag))
	blank_array_range(spectrum_mag, peak1_n, mute_offset_n)

	#peak2_n_boundary = max(0, peak1_n - mute_offset_n)
	#peak2_n = numpy.argmax(spectrum_mag[:peak2_n_boundary])
	peak2_n = numpy.argmax(spectrum_mag)
	peak2_hz = arg_hz(peak2_n)
	peak2_mag = spectrum_mag[peak2_n]
	#peak2_avg = sum(spectrum_mag[peak2_n-mute_offset_n:peak2_n+mute_offset_n]) / (2 * mute_offset_n)
	#print('peak 2: %s %s' % (peak2_hz, peak2_mag))
	blank_array_range(spectrum_mag, peak2_n, mute_offset_n)

	#peak3_n_boundary = min(len(spectrum_mag), peak1_n + mute_offset_n)
	#peak3_n = numpy.argmax(spectrum_mag[peak3_n_boundary:]) + peak3_n_boundary
	peak3_n = numpy.argmax(spectrum_mag)
	peak3_hz = arg_hz(peak3_n)
	peak3_mag = spectrum_mag[peak3_n]
	#peak3_avg = sum(spectrum_mag[peak3_n-mute_offset_n:peak3_n+mute_offset_n]) / (2 * mute_offset_n)
	#print('peak 3: %s %s' % (peak3_hz, peak3_mag))
	#blank_array_range(spectrum_mag, peak3_n, mute_offset_n)

	#print('lobes: %s / %s' % (peak2_avg, peak3_avg))

	peak23_hz_avg = (peak2_hz + peak3_hz) / 2.0

	# peak_threshold = spectrum_mag_avg * 5.0
	# peaks = [x for x in spectrum_mag if x > peak_threshold]
	# total_weight = len(peaks)
	# if total_weight > 0:
	# 	centroid = sum([arg_hz(i) for i in range(len(spectrum_mag)) if spectrum_mag[i] > peak_threshold])
	# 	print(total_weight, centroid, centroid / total_weight)
	# else:
	# 	print('too much noise')

	result = {}
	# result['modulation_alt'] = modulation_alt

	# If all three peaks are within 1kHz, it's probably AM.
	is_ask = abs(peak1_hz - peak23_hz_avg) < 1e3

	# is_ask = k1 > 3.2
	# is_fsk = not is_ask

	if is_ask:
		shift_hz = peak1_hz
		baud_rate = (abs(peak3_hz - peak1_hz) + abs(peak2_hz - peak1_hz)) / 2.0
		result['modulation'] = 'ask'
		result['carrier'] = shift_hz
		result['baud_rate'] = baud_rate
	else:
		peak2_1_delta = peak1_n - peak2_n
		peak1_3_delta = peak3_n - peak1_n

		# peak2_1_avg = sum(spectrum_mag[peak2_n:peak1_n]) / float(peak2_1_delta)
		# print('peak2_1_avg:', peak2_1_avg)
		# peak1_3_avg = sum(spectrum_mag[peak1_n:peak3_n]) / float(peak1_3_delta)
		# print('peak1_3_avg:', peak1_3_avg)

		# print('lo lobe mag:', spectrum_mag[peak2_n - peak1_3_delta])
		# print('hi lobe mag:', spectrum_mag[peak3_n + peak2_1_delta])

		# peak_lo_lobe_avg = sum(spectrum_mag[peak2_n - peak1_3_delta:peak2_n]) / float(peak1_3_delta)
		# peak_lo_1_3_ratio = peak_lo_lobe_avg / peak1_3_avg
		# print('peak_lo_lobe_avg:', peak_lo_lobe_avg)
		# print('low lobe ratio:', peak_lo_1_3_ratio)
		# peak_hi_lobe_avg = sum(spectrum_mag[peak3_n:peak3_n + peak2_1_delta]) / float(peak2_1_delta)
		# peak_hi_2_1_ratio = peak_hi_lobe_avg / peak2_1_avg
		# print('peak_hi_lobe_avg:', peak_hi_lobe_avg)
		# print('high lobe ratio:', peak_hi_2_1_ratio)

		# peak1_3_center_n = int(round((peak1_n + peak3_n) / 2.0))
		# peak1_3_center_lo_avg = sum(spectrum_mag[peak1_n:peak1_3_center_n]) / float(peak1_3_center_n - peak1_n)
		# peak1_3_center_hi_avg = sum(spectrum_mag[peak1_3_center_n:peak3_n]) / float(peak3_n - peak1_3_center_n)
		# peak1_3_center_ratio = peak1_3_center_lo_avg / peak1_3_center_hi_avg
		# print('peak1_3 center avg:', peak1_3_center_lo_avg, peak1_3_center_hi_avg, peak1_3_center_ratio)
		# peak2_1_center_n = int(round((peak2_n + peak1_n) / 2.0))
		# peak2_1_center_lo_avg = sum(spectrum_mag[peak2_n:peak2_1_center_n]) / float(peak2_1_center_n - peak2_n)
		# peak2_1_center_hi_avg = sum(spectrum_mag[peak2_1_center_n:peak1_n]) / float(peak1_n - peak2_1_center_n)
		# peak2_1_center_ratio = peak2_1_center_lo_avg / peak2_1_center_hi_avg
		# print('peak2_1 center avg:', peak2_1_center_lo_avg, peak2_1_center_hi_avg, peak2_1_center_ratio)

		# Mirroring stuff for correlation?
		# spectrum_mag[peak2_n:peak2_1_center_n]
		# spectrum_mag[peak1_n:peak2_1_center_n:-1]

		#other_peak_hz = peak3_hz if peak3_mag > peak2_mag else peak2_hz
		if peak2_1_delta > peak1_3_delta:
			other_peak_hz = peak2_hz
		else:
			other_peak_hz = peak3_hz

		shift_hz = (peak1_hz + other_peak_hz) / 2.0
		diff_hz = abs(other_peak_hz - peak1_hz)
		deviation_hz = diff_hz / 2.0




		# translated = numpy.arange(len(data), dtype=numpy.float32) * 2.0j * numpy.pi * -shift_hz / sampling_rate
		# translated = numpy.exp(translated) * data
		# fm_demod = numpy.angle(translated[1:] * numpy.conjugate(translated[:-1]))
		# x = numpy.arange(len(fm_demod)) * (1.0 / sampling_rate)
		# # plot(spectrum_mag)
		# plot(x, fm_demod)
		# show()




		result['modulation'] = 'fsk'
		result['carrier'] = shift_hz
		result['deviation'] = deviation_hz

	# print('%s: %s %s' % (
	# 	result['modulation'],
	# 	result['carrier'],
	# 	result['deviation'] if 'deviation' in result else result['baud_rate'],
	# ))

	#print('%s / %s (%s)' % (result['modulation_alt'], result['modulation'], gamma_max))

	# pyplot.subplot(411)
	# x = numpy.arange(len(data)) / sampling_rate
	# pyplot.plot(x, numpy.absolute(data))

	# pyplot.subplot(412)
	# fm_demod = numpy.angle(data[1:] * numpy.conjugate(data[:-1]))
	# x = numpy.arange(len(fm_demod)) / sampling_rate
	# pyplot.plot(x, fm_demod)
	
	# pyplot.subplot(413)
	# x = numpy.fft.fftshift(numpy.fft.fftfreq(len(data))) * sampling_rate
	# mag = numpy.absolute(numpy.fft.fftshift(numpy.fft.fft(data)))
	# db = numpy.log10(mag) * 10.0
	# mag_max = max(mag)
	# mag_avg = sum(mag) / len(mag)
	# snr = math.log10(mag_max / mag_avg) * 10.0
	# print('SNR: %f - %f = %f' % (mag_max, mag_avg, snr))
	# pyplot.plot(x, db)

	# pyplot.subplot(414)
	# correlation = scipy.signal.correlate(spectrum_mag, spectrum_mag[::-1])
	# correlation_n = numpy.argmax(correlation) - len(correlation) / 2.0
	# print(correlation_n)
	# #convolution_f = float(convolution_n) / len(spectrum_mag) / 2.0 * sampling_rate
	# pyplot.plot(correlation)
	# pyplot.show()

	# cwt = scipy.signal.cwt(data, scipy.signal.ricker, (10, 11,))
	# pyplot.plot(cwt)
	# pyplot.show()

	return result
