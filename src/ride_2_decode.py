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
from collections import defaultdict

import pytz
from iso8601 import iso8601

import crcmod

def split_string_bytes(data, start_offset):
	for n in range(start_offset, len(data), 8):
		yield data[n:n+8]

crc8 = crcmod.mkCrcFun(0x107, rev=False, initCrc=0, xorOut=0)

decoded_data = []

for packet_info in sys.stdin:
	timestamp, access_code, payload, modulation, f_offset, deviation, bit_rate, filename = packet_info.split()
	timestamp = iso8601.parse_date(timestamp)
	payload_bytes_str = tuple(split_string_bytes(payload, 5))
	payload_bytes = map(lambda v: int(v, 2), payload_bytes_str)
	payload_str = ''.join(map(chr, payload_bytes))
	pressure = payload_bytes[0] / 5.0
	temperature = payload_bytes[1]
	device_id = ''.join(payload_bytes_str[2:6])
	flags = payload_bytes[6]
	calculated_crc = crc8(payload_str[0:7])
	packet_crc = payload_bytes[7]
	crc_ok = (calculated_crc == packet_crc)

	if crc_ok:
		print('%s %s %.1f %d %d' % (
			timestamp.isoformat(),
			device_id,
			pressure,
			temperature,
			flags,
		))
