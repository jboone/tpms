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

from gnuradio import blks2
from gnuradio import blocks
from gnuradio import digital
from gnuradio import eng_notation
from gnuradio import filter
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from gnuradio.gr import firdes
#from gnuradio.wxgui import forms
#from gnuradio.wxgui import scopesink2
#from grc_gnuradio import wxgui as grc_wxgui
from optparse import OptionParser
#import wx

import numpy
import sys

from bit_coding import *
from packet import Packetizer

class top_block(gr.top_block):

	def __init__(self, filepath_in):
		gr.top_block.__init__(self)
		#grc_wxgui.top_block_gui.__init__(self, title="Top Block")

		##################################################
		# Variables
		##################################################
		self.samp_rate = samp_rate = 200e3
		self.bb_interpolation = bb_interpolation = 100
		self.bb_decimation = bb_decimation = 612
		self.samples_per_symbol = samples_per_symbol = 4
		self.gain_mu = gain_mu = 0.03
		self.bb_rate = bb_rate = float(samp_rate) * bb_interpolation / bb_decimation
		self.bb_filter_freq = bb_filter_freq = 10e3
		self.omega = omega = samples_per_symbol
		self.mu = mu = 0.5
		self.gain_omega = gain_omega = 0.25 * gain_mu * gain_mu
		self.bb_taps = bb_taps = gr.firdes.low_pass(1.0, samp_rate, bb_filter_freq, bb_filter_freq * 0.1)
		self.baud_rate = baud_rate = bb_rate / samples_per_symbol
		#self.average = average = 64

		##################################################
		# Blocks
		##################################################
		# self.wxgui_scopesink2_1_0_0 = scopesink2.scope_sink_f(
		# 			self.GetWin(),
		# 			title="Scope Plot",
		# 			sample_rate=baud_rate,
		# 			v_scale=0,
		# 			v_offset=0,
		# 			t_scale=0,
		# 			ac_couple=False,
		# 			xy_mode=False,
		# 			num_inputs=1,
		# 			trig_mode=gr.gr_TRIG_MODE_NORM,
		# 			y_axis_label="Counts",
		# 		)
		# self.Add(self.wxgui_scopesink2_1_0_0.win)
		#self.freq_xlating_fir_filter_xxx_0 = filter.freq_xlating_fir_filter_ccc(1, (bb_taps), 6e3, samp_rate)
		self.digital_correlate_access_code_bb_0 = digital.correlate_access_code_bb("10101010101010101010101010101", 1)
		self.digital_clock_recovery_mm_xx_0 = digital.clock_recovery_mm_ff(omega, gain_omega, mu, gain_mu, 0.0002)
		self.digital_binary_slicer_fb_0 = digital.binary_slicer_fb()
		self.dc_blocker_xx_0 = filter.dc_blocker_ff(64, True)
		#self.blocks_uchar_to_float_0_0 = blocks.uchar_to_float()
		#self.blocks_throttle_0 = blocks.throttle(gr.sizeof_gr_complex*1, samp_rate)
		#self.blocks_file_source_0_0 = blocks.file_source(gr.sizeof_gr_complex*1, "/mnt/hgfs/tmp/rf_captures/315.000m_200.000k_20130623_133451_extract_am_2.cfile", True)
		self.blocks_file_source_0_0 = blocks.file_source(gr.sizeof_gr_complex*1, filepath_in, False)
		self.blocks_complex_to_mag_0 = blocks.complex_to_mag(1)
		self.blks2_rational_resampler_xxx_0 = blks2.rational_resampler_fff(
			interpolation=bb_interpolation,
			decimation=bb_decimation,
			taps=None,
			fractional_bw=None,
		)
		# _bb_filter_freq_sizer = wx.BoxSizer(wx.VERTICAL)
		# self._bb_filter_freq_text_box = forms.text_box(
		# 	parent=self.GetWin(),
		# 	sizer=_bb_filter_freq_sizer,
		# 	value=self.bb_filter_freq,
		# 	callback=self.set_bb_filter_freq,
		# 	label="BB Freq",
		# 	converter=forms.int_converter(),
		# 	proportion=0,
		# )
		# self._bb_filter_freq_slider = forms.slider(
		# 	parent=self.GetWin(),
		# 	sizer=_bb_filter_freq_sizer,
		# 	value=self.bb_filter_freq,
		# 	callback=self.set_bb_filter_freq,
		# 	minimum=5e3,
		# 	maximum=30e3,
		# 	num_steps=250,
		# 	style=wx.SL_HORIZONTAL,
		# 	cast=int,
		# 	proportion=1,
		# )
		# self.Add(_bb_filter_freq_sizer)
		# _average_sizer = wx.BoxSizer(wx.VERTICAL)
		# self._average_text_box = forms.text_box(
		# 	parent=self.GetWin(),
		# 	sizer=_average_sizer,
		# 	value=self.average,
		# 	callback=self.set_average,
		# 	label="Average Length",
		# 	converter=forms.int_converter(),
		# 	proportion=0,
		# )
		# self._average_slider = forms.slider(
		# 	parent=self.GetWin(),
		# 	sizer=_average_sizer,
		# 	value=self.average,
		# 	callback=self.set_average,
		# 	minimum=0,
		# 	maximum=256,
		# 	num_steps=256,
		# 	style=wx.SL_HORIZONTAL,
		# 	cast=int,
		# 	proportion=1,
		# )
		# self.Add(_average_sizer)

		##################################################
		# Connections
		##################################################
		self.connect((self.digital_clock_recovery_mm_xx_0, 0), (self.digital_binary_slicer_fb_0, 0))
		self.connect((self.digital_binary_slicer_fb_0, 0), (self.digital_correlate_access_code_bb_0, 0))
		#self.connect((self.digital_correlate_access_code_bb_0, 0), (self.blocks_uchar_to_float_0_0, 0))
		#self.connect((self.blocks_throttle_0, 0), (self.freq_xlating_fir_filter_xxx_0, 0))
		#self.connect((self.freq_xlating_fir_filter_xxx_0, 0), (self.blocks_complex_to_mag_0, 0))
		self.connect((self.blocks_complex_to_mag_0, 0), (self.blks2_rational_resampler_xxx_0, 0))
		self.connect((self.blks2_rational_resampler_xxx_0, 0), (self.dc_blocker_xx_0, 0))
		self.connect((self.dc_blocker_xx_0, 0), (self.digital_clock_recovery_mm_xx_0, 0))
		#self.connect((self.blocks_uchar_to_float_0_0, 0), (self.wxgui_scopesink2_1_0_0, 0))
		#self.connect((self.blocks_file_source_0_0, 0), (self.blocks_throttle_0, 0))
		#self.connect((self.blocks_file_source_0_0, 0), (self.freq_xlating_fir_filter_xxx_0, 0))
		self.connect((self.blocks_file_source_0_0, 0), (self.blocks_complex_to_mag_0, 0))
		
		self.packetizer = Packetizer(82)
		self.connect((self.digital_correlate_access_code_bb_0, 0), (self.packetizer, 0))


	def get_samp_rate(self):
		return self.samp_rate

	def set_samp_rate(self, samp_rate):
		self.samp_rate = samp_rate
		self.set_bb_rate(float(self.samp_rate) * self.bb_interpolation / self.bb_decimation)
		self.set_bb_taps(gr.firdes.low_pass(1.0, self.samp_rate, self.bb_filter_freq, self.bb_filter_freq * 0.1))
		self.blocks_throttle_0.set_sample_rate(self.samp_rate)

	def get_bb_interpolation(self):
		return self.bb_interpolation

	def set_bb_interpolation(self, bb_interpolation):
		self.bb_interpolation = bb_interpolation
		self.set_bb_rate(float(self.samp_rate) * self.bb_interpolation / self.bb_decimation)

	def get_bb_decimation(self):
		return self.bb_decimation

	def set_bb_decimation(self, bb_decimation):
		self.bb_decimation = bb_decimation
		self.set_bb_rate(float(self.samp_rate) * self.bb_interpolation / self.bb_decimation)

	def get_samples_per_symbol(self):
		return self.samples_per_symbol

	def set_samples_per_symbol(self, samples_per_symbol):
		self.samples_per_symbol = samples_per_symbol
		self.set_baud_rate(self.bb_rate / self.samples_per_symbol)
		self.set_omega(self.samples_per_symbol)

	def get_gain_mu(self):
		return self.gain_mu

	def set_gain_mu(self, gain_mu):
		self.gain_mu = gain_mu
		self.digital_clock_recovery_mm_xx_0.set_gain_mu(self.gain_mu)
		self.set_gain_omega(0.25 * self.gain_mu * self.gain_mu)

	def get_bb_rate(self):
		return self.bb_rate

	def set_bb_rate(self, bb_rate):
		self.bb_rate = bb_rate
		self.set_baud_rate(self.bb_rate / self.samples_per_symbol)

	def get_bb_filter_freq(self):
		return self.bb_filter_freq

	def set_bb_filter_freq(self, bb_filter_freq):
		self.bb_filter_freq = bb_filter_freq
		self._bb_filter_freq_slider.set_value(self.bb_filter_freq)
		self._bb_filter_freq_text_box.set_value(self.bb_filter_freq)
		self.set_bb_taps(gr.firdes.low_pass(1.0, self.samp_rate, self.bb_filter_freq, self.bb_filter_freq * 0.1))

	def get_omega(self):
		return self.omega

	def set_omega(self, omega):
		self.omega = omega
		self.digital_clock_recovery_mm_xx_0.set_omega(self.omega)

	def get_mu(self):
		return self.mu

	def set_mu(self, mu):
		self.mu = mu
		self.digital_clock_recovery_mm_xx_0.set_mu(self.mu)

	def get_gain_omega(self):
		return self.gain_omega

	def set_gain_omega(self, gain_omega):
		self.gain_omega = gain_omega
		self.digital_clock_recovery_mm_xx_0.set_gain_omega(self.gain_omega)

	def get_bb_taps(self):
		return self.bb_taps

	def set_bb_taps(self, bb_taps):
		self.bb_taps = bb_taps
		self.freq_xlating_fir_filter_xxx_0.set_taps((self.bb_taps))

	def get_baud_rate(self):
		return self.baud_rate

	def set_baud_rate(self, baud_rate):
		self.baud_rate = baud_rate
		self.wxgui_scopesink2_1_0_0.set_sample_rate(self.baud_rate)

	def get_average(self):
		return self.average

	def set_average(self, average):
		self.average = average
		self._average_slider.set_value(self.average)
		self._average_text_box.set_value(self.average)

if __name__ == '__main__':
	parser = OptionParser(option_class=eng_option, usage="%prog: [options]")
	(options, args) = parser.parse_args()
	tb = top_block(sys.argv[1])
	#tb.Run(True)
	tb.run()
	