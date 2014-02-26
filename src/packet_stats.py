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
import math
from collections import defaultdict
from argparse import ArgumentParser

import pytz
from iso8601 import iso8601

from bit_coding import *

def split_string_bytes(data, start_offset):
	yield data[:start_offset]
	for n in range(start_offset, len(data), 8):
		yield data[n:n+8]

parser = ArgumentParser()
parser.add_argument('-l', '--length', type=int, default=None, help="Required packet decoded symbol length (longer packets will be truncated)")
parser.add_argument('-e', '--encoding', type=str, default='raw', help="Bit encoding (man, diffman)")
parser.add_argument('--decoded', action="store_true", help="Display decoded packets")
parser.add_argument('--ruler', action="store_true", help="Display bit-index ruler along with decoded packets")
parser.add_argument('--lengthstats', action="store_true", help="Display statistics on packet length distribution")
parser.add_argument('--bitstats', action="store_true", help="Display statistics on each bit across all packets")
parser.add_argument('--brutecrc', type=int, default=None, help="Display packet data for brute force CRC, with packet occurrence above threshold")
parser.add_argument('--rangestats', type=str, default=None, help="Display statistics on a range of bits")
parser.add_argument('-v', '--verbose', action="store_true", default=False, help="Show more detail (if available)")
args = parser.parse_args()

if args.rangestats:
	args.rangestats = tuple(map(int, args.rangestats.split(',')))

decoder_map = {
	'man': manchester_decode,
	'diffman': differential_manchester_decode,
	'raw': lambda s: s,
}
decoder_fn = decoder_map[args.encoding]

packet_length_counts = defaultdict(int)
unique_packet_counts = defaultdict(int)

if args.length:
	byte_stats = [defaultdict(int) for n in range(int(math.ceil(args.length / 8.0)))]
	packet_first_byte_offset = args.length % 8

decoded_packets = []

packet_fields = ('timestamp', 'access_code', 'payload', 'modulation', 'carrier', 'deviation', 'symbol_rate', 'filename')

ruler_interval = 5

for packet_line in sys.stdin:
	packet_line = packet_line.strip()

	# TODO: Hack to skip the VOLK message that GNU Radio insists on writing to stdout.
	if packet_line.startswith('Using Volk machine: '):
		continue

	packet = dict(zip(packet_fields, packet_line.split()))
	packet['timestamp'] = iso8601.parse_date(packet['timestamp'])
	packet['carrier'] = float(packet['carrier'])
	packet['deviation'] = float(packet['deviation'])
	packet['symbol_rate'] = float(packet['symbol_rate'])

	packet['payload'] = decoder_fn(packet['payload']).split('X')[0]

	if len(packet['payload']) == 0:
		continue

	if args.length:
		if len(packet['payload']) < args.length:
			continue
		# Truncate
		packet['payload'] = packet['payload'][:args.length]
		bytes = tuple(split_string_bytes(packet['payload'], packet_first_byte_offset))

		for n in range(len(bytes)):
			byte_stats[n][bytes[n]] += 1

	decoded_packets.append(packet)

	packet_length_counts[len(packet['payload'])] += 1
	unique_packet_counts[packet['payload']] += 1

	if args.decoded:
		if args.ruler and (packet_count % ruler_interval) == 0:
			s = []
			for i in range(10):
				s.append('%d----+----' % i)
			print(''.join(s))
		if args.verbose:
			print('%s %s %s %s %d %d %d %s' % (
				packet['timestamp'].isoformat(),
				packet['access_code'],
				packet['payload'],
				packet['modulation'],
				packet['carrier'],
				packet['deviation'],
				packet['symbol_rate'],
				packet['filename'],
			))
		else:
			print(packet['payload'])

# if unique_packet_counts:
# 	print('Unique packets')
# 	for payload in sorted(unique_packet_counts.keys(), key=lambda a: len(a)):
# 		count = unique_packet_counts[payload]
# 		if args.length:
# 			payload_bytes_str = tuple(split_string_bytes(payload, packet_first_byte_offset))
# 			payload_bytes = map(lambda s: int(s, 2), payload_bytes_str)
# 			payload_sum = sum(payload_bytes[:-1])
# 			payload_sum_trunc = payload_sum & 0xff
# 			checksum = payload_bytes[-1]
# 			payload_sum_minus_checksum = payload_sum - checksum
# 			payload_sum_minus_checksum_trunc = payload_sum_minus_checksum & 0xff
# 			# TODO: Check for Hamming distance in payload and candidate checksum field.
# 			print('%s %4d sum=%s(%3d) diff=%s(%3d)' % (
# 				' '.join(payload_bytes_str), count,
# 				'{:0>8b}'.format(payload_sum_trunc), payload_sum_trunc,
# 				'{:0>8b}'.format(payload_sum_minus_checksum_trunc), payload_sum_minus_checksum_trunc
# 			))
# 		else:
# 			print(payload)
# 	print

if args.lengthstats:
	print('Length statistics:')
	for n in sorted(packet_length_counts):
		print('\t%d: %d' % (n, packet_length_counts[n]))
	print

if args.brutecrc:
	for payload in sorted(unique_packet_counts.keys(), key=lambda a: unique_packet_counts[a], reverse=True):
		count = unique_packet_counts[payload]
		if count > args.brutecrc:
			print(payload)

if args.bitstats:
	print('Bit value statistics:')
	bit_stats = defaultdict(lambda: [0, 0])
	for payload in unique_packet_counts.keys():
		for n in range(len(payload)):
			value = payload[n]
			bit_stats[n][int(value)] += 1
	for n in sorted(bit_stats.keys()):
		stats = bit_stats[n]
		stat_h = stats[1]
		stat_l = stats[0]
		ratio_1 = float(stat_h) / float(stat_h + stat_l)
		bar = '*' * int(round(ratio_1 * 20))
		print('\t%3d: %4d/%4d %4d %5.1f%% %s' % (n, stat_h, stat_l, stat_h+stat_l, ratio_1 * 100, bar))
	print

if args.rangestats:
	if args.ruler:
		s = ' ' * args.rangestats[0] + '^' * (args.rangestats[1] - args.rangestats[0])
		print(s)
	print('Range %d:%d' % args.rangestats)
	range_stats = defaultdict(int)
	for payload in unique_packet_counts.keys():
		range_value = payload[args.rangestats[0]:args.rangestats[1]]
		range_stats[range_value] += unique_packet_counts[payload]
	for key in sorted(range_stats):
		print('%9x %12d %s: %3d %s' % (int(key, 2), int(key, 2), key, range_stats[key], '*' * range_stats[key]))
	print

# if args.length:
# 	print('Byte value statistics:')
# 	for n in range(len(byte_stats)):
# 		print('\tbyte %d:' % n)
# 		for key in sorted(byte_stats[n].keys()):
# 			count = byte_stats[n][key]
# 			print('\t\t%s: %d' % (key, count))
# 	print
