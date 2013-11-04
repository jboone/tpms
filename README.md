TPMS
====

Software for capturing, demodulating, decoding, and assessing data from
automotive tire pressure monitors.

Tire pressure monitoring systems (TPMS) are becoming common on automobiles,
and in certain countries, are required as a condition of sale. Most TPMS
devices use simple wireless communication techniques such as:

* FSK modulation
* Manchester bit coding
* Small CRCs or checksums
* Unique device identifiers

Requirements
============

This software was developed for and tested with:

* GNU Radio 3.7.1
* Python 2.7
* PySide 1.2.0 (Qt bindings for Python)
* bruteforce-crc (for finding CRC polynomials and other characteristics)
* crcmod (CRC library for Python)
* Matplotlib (for graphing data)

Using
=====

Capture data from a vehicle with a software radio receiver like an RTL-SDR USB dongle, or a HackRF, or other device capable of capturing approximately 1MHz of complex spectrum from 315MHz or 433MHz. The best way to constrain packets received to only one vehicle is to ride in the vehicle as it is driven.

Extract bursts of data from the raw capture:

    extract_bursts <filename>.cfile

Visually inspect bursts and assess modulation characteristics (ASK/FSK, carrier frequency, deviation, bit rate, access code or preamble):

    burst_inspect.py tpms_314.950m_0.400m_20131013_180516z_rtlsdr/

Demodulate packets with certain characteristics, into raw bit streams:

    tpms_fsk.py --rate 400000 --modulation fsk --carrier 53000 --deviation 33000 --symbol-rate 20150 --preamble 1101101011100 */*.cfile | tee demodulated.txt

Examine statistics of packet lengths, assuming Manchester decoding (the most common type of TPMS bit coding):

    cat demodulated.txt | packet_stats.py --encoding man --lengthstats

Examine 0/1 distribution of each decoded bit, across all packets:

    cat demodulated.txt | packet_stats.py --encoding man --length 70 --bitstats

Make and test some assumptions regarding ranges of bits. First, test 32-bit ranges to find bits that possess only four unique values (one ID for each tire):

    cat demodulated.txt | packet_stats.py --encoding man --length 70 --rangestats 0,32
    cat demodulated.txt | packet_stats.py --encoding man --length 70 --rangestats 1,33
    cat demodulated.txt | packet_stats.py --encoding man --length 70 --rangestats 21,53

Test assumptions about other ranges of bits, using an oft-valid assumption that fields break on byte boundaries. Graph distribution of data and look for data that might represent tire pressure and temperature, or perhaps a CRC or checksum:

    cat demodulated.txt | packet_stats.py --encoding man --length 70 --decode | grep 1000110011000 | packet_graph.py --range 5,13
    cat demodulated.txt | packet_stats.py --encoding man --length 70 --decode | grep 1000110011000 | packet_graph.py --range 13,21
    cat demodulated.txt | packet_stats.py --encoding man --length 70 --decode | grep 1000110011000 | packet_graph.py --range 61,69

If a CRC or checksum field is identified, test for possible CRC polynomials and other characteristics by using bruteforce-crc:

    cat demodulated.txt | packet_stats.py --encoding man --length 70 --brutecrc 2 | tee brute.txt
    bruteforce-crc --file brute.txt --width 8 --start 5 --end 61 --offs-crc 61

Export decoded packet data and graph using knowledge acquired above:

    cat demodulated.txt | packet_stats.py --encoding man --length 70 --decoded | tee decoded.txt
    cat decoded.txt | ride_2_decode.py | ride_2_graph.py

Notes and Things to Investigate
===============================

Another CRC reversing package: http://reveng.sourceforge.net

Liquid-DSP library for building efficient software defined radio implementations, perhaps on the HackRF ARM Cortex-M4F: https://github.com/jgaeddert/liquid-dsp

License
=======

The associated software is provided under a GPLv2 license:

Copyright (C) 2013 Jared Boone, ShareBrained Technology, Inc.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301, USA.

Contact
=======

Jared Boone <jared@sharebrained.com>

ShareBrained Technology, Inc.

<http://www.sharebrained.com/>


The latest version of this repository can be found at
https://github.com/jboone/tpms
