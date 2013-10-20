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
import pytz
from iso8601 import iso8601


def decode_packet_candidates(packet_info, decoder_fns):
	results = {}

	for decoder_fn in decoder_fns:
		decoded_set = set()
		for actual_access_code, data in packet_info:
			decoded = decoder_fn(data)
			decoded = ''.join(decoded)
			decoded = decoded.split('X')[0]
			if len(decoded) >= 32:
				#print('R %s %s' % (''.join(map(str, actual_access_code)), ''.join(map(str, data))))
				decoded_set.add(decoded)

		if decoded_set:
			results[decoder_fn.__name__] = decoded_set

	return results

packet_data = open(sys.argv[1], 'r')

for packet_info in packet_data:
	timestamp, encoding, access_code, payload, modulation, f_offset, deviation, bit_rate, filename = packet_info.split()
	timestamp = iso8601.parse_date(timestamp)

	decoded_packets = decode_packet_candidates(packet_info,
		(manchester_decode, differential_manchester_decode)
	)
	for decoder_type, decoder_data in decoded_packets.iteritems():
		results.append({
			'decoder': decoder_type,
			'data': decoder_data,
			'carrier': carrier_hz,
			'modulation': 'fsk',
			'symbol_rate': symbol_rate,
			'deviation': deviation,
			'access_code': access_code,
		})

	print(timestamp)