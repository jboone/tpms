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

from matplotlib import pyplot

from iso8601 import iso8601

decoded_data = []
for line in sys.stdin:
	line = line.split()
	item = {
		'timestamp': iso8601.parse_date(line[0]),
		'device_id': line[1],
		'value_1': float(line[2]),
		'value_2': float(line[3]),
		'flags': int(line[4]),
	}
	decoded_data.append(item)

by_device = defaultdict(list)
for item in decoded_data:
	by_device[item['device_id']].append(item)

pyplot.subplot(211)
pyplot.title('Value 1')
pyplot.xlabel('Time UTC')
pyplot.ylabel('???')
for device_id, items in by_device.iteritems():
	items = sorted(items, key=lambda v: v['timestamp'])
	by_device[device_id] = items
	x = [item['timestamp'] for item in items]
	y = [item['value_1'] for item in items]
	pyplot.plot(x, y, label=device_id)

pyplot.subplot(212)
pyplot.title('Value 2')
pyplot.xlabel('Time UTC')
pyplot.ylabel('???')
for device_id, items in by_device.iteritems():
	items = sorted(items, key=lambda v: v['timestamp'])
	by_device[device_id] = items
	x = [item['timestamp'] for item in items]
	y = [item['value_2'] for item in items]
	pyplot.plot(x, y, label=device_id)

pyplot.show()