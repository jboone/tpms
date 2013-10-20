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

import sys
from argparse import ArgumentParser

from iso8601 import iso8601

from matplotlib import pyplot

parser = ArgumentParser()
parser.add_argument('--range', type=str, help="Range of bits to graph")
args = parser.parse_args()

args.range = tuple(map(int, args.range.split(',')))

decoded_packets = []

packet_fields = ('timestamp', 'access_code', 'payload', 'modulation', 'carrier', 'deviation', 'symbol_rate', 'filename')

for packet_line in sys.stdin:
	packet = dict(zip(packet_fields, packet_line.split()))
	packet['timestamp'] = iso8601.parse_date(packet['timestamp'])
	packet['carrier'] = float(packet['carrier'])
	packet['deviation'] = float(packet['deviation'])
	packet['symbol_rate'] = float(packet['symbol_rate'])

	decoded_packets.append(packet)

pyplot.title('Range %d:%d' % args.range)
pyplot.xlabel('Time UTC')
pyplot.ylabel('Value')
x = []
y = []
for packet in sorted(decoded_packets, key=lambda a: a['timestamp']):
	x.append(packet['timestamp'])
	y.append(int(packet['payload'][args.range[0]:args.range[1]], 2))
pyplot.plot(x, y)
pyplot.show()
