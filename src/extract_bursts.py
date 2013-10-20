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
from gnuradio import eng_notation
from gnuradio import filter
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from optparse import OptionParser
import math
import sys
import os.path
import datetime
import pytz
from iso8601 import iso8601

from burst_detector import *

class top_block(gr.top_block):

    def __init__(self, source_path):
        gr.top_block.__init__(self, "Top Block")

        source_directory, source_filename = os.path.split(source_path)
        source_filename, source_extension = os.path.splitext(source_filename)
        target_signal, carrier_freq, sampling_rate, start_date, start_time, capture_device = source_filename.split('_')

        if sampling_rate[-1].upper() == 'M':
            sampling_rate = float(sampling_rate[:-1]) * 1e6
        else:
            raise RuntimeError('Unsupported sampling rate "%s"' % sampling_rate)

        start_timestamp = iso8601.datetime.strptime(start_date + ' ' + start_time, '%Y%m%d %H%M%Sz')
        utc = pytz.utc
        start_timestamp = utc.localize(start_timestamp)
        f_ts = open('timestamp.txt', 'w')
        f_ts.write(start_timestamp.isoformat())
        f_ts.close()

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = sampling_rate
        self.average_window = average_window = 1000

        ##################################################
        # Blocks
        ##################################################
        self.blocks_file_source_0 = blocks.file_source(gr.sizeof_gr_complex*1, source_path, False)
        self.burst_detector = burst_detector()
        self.blocks_tagged_file_sink_0 = blocks.tagged_file_sink(gr.sizeof_gr_complex*1, samp_rate)

        ##################################################
        # Connections
        ##################################################
        self.connect((self.blocks_file_source_0, 0), (self.burst_detector, 0))
        self.connect((self.burst_detector, 0), (self.blocks_tagged_file_sink_0, 0))

if __name__ == '__main__':
    parser = OptionParser(option_class=eng_option, usage="%prog: [options]")
    (options, args) = parser.parse_args()
    tb = top_block(sys.argv[1])
    tb.start()
    tb.wait()

