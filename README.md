# TPMS

Software for capturing, demodulating, decoding, and assessing data from
automotive tire pressure monitors.

Tire pressure monitoring systems (TPMS) are becoming common on automobiles,
and in certain countries, are required as a condition of sale. Most TPMS
devices use simple wireless communication techniques such as:

* FSK modulation
* Manchester bit coding
* Small CRCs or checksums
* Unique device identifiers

# Background

For more background on this project, please watch Jared Boone's talk from ToorCon 15:

[Dude, Where's My Car?: Reversing Tire Pressure Monitors with a Software Defined Radio](http://www.youtube.com/watch?v=bKqiq2Y43Wg)

...or this interview with Darren Kitchen of Hak5:

[Hak5 1511 – Tracking Cars Wirelessly And Intercepting Femtocell Traffic](http://hak5.org/episodes/hak5-1511)

# Software

This software was developed for and tested with:

* [rtl-sdr](http://sdr.osmocom.org/trac/wiki/rtl-sdr)
* [GNU Radio](http://gnuradio.org) 3.7.1
* [Python](http://python.org) 2.7
* [NumPy](http://numpy.scipy.org/) Numerical Python library.
* [SciPy](http://scipy.org/scipylib/) Scientific Python library.
* [PyFFTW](http://hgomersall.github.io/pyFFTW/) Python interface to FFTW.
* [FFTW](http://www.fftw.org) Fastest FFT in the West.
* [PyTZ](http://pytz.sourceforge.net) Timezone library.
* [PyISO8601](https://bitbucket.org/micktwomey/pyiso8601/) Python ISO8601 date/time parsing library.
* [PySide](http://qt-project.org/wiki/PySide) 1.2.0, Qt bindings for Python.
* [bruteforce-crc](https://github.com/sitsec/bruteforce-crc), for finding CRC polynomials and other characteristics.
* [crcmod](http://crcmod.sourceforge.net), CRC library for Python.
* [Matplotlib](http://matplotlib.org), for graphing data.

# Hardware

I used a variety of hardware for receiving tire pressure monitors. If you don't already
have a software-defined radio receiver, a $50 US investment is all you need to get started.

### Quick Shopping List for The Impatient

Aside from a computer capable of running GNU Radio, here's what you'll need:

* [NooElec TV28T v2 DVB-T USB Stick (R820T) w/ Antenna and Remote Control](http://www.nooelec.com/store/software-defined-radio/tv28tv2.html) or [Hacker Warehouse DVB-T USB 2.0](http://hackerwarehouse.com/product/dvb-t-usb2-0/)
* [NooElec Male MCX to Female SMA Adapter](http://www.nooelec.com/store/software-defined-radio/male-mcx-to-female-sma-adapter.html)
* [Linx Technologies ANT-315-CW-RH-SMA 315MHz 51mm (2") helical whip antenna, SMA](http://mouser.com/Search/Refine.aspx?Keyword=ANT-315-CW-RH-SMA) or [Linx Technologies ANT-433-CW-RH-SMA 433MHz 51mm (2") helical whip antenna, SMA](http://mouser.com/Search/Refine.aspx?Keyword=ANT-433-CW-RH-SMA)
* [Johnson / Emerson Connectivity Solutions 415-0031-024 SMA male to SMA female cable, 61cm (24")](http://mouser.com/Search/Refine.aspx?Keyword=415-0031-024), (Optional, if you don't want your antenna sticking straight out of your USB receiver dongle.)

### Receiver

If you're just getting started with SDR, I highly recommend getting a DVB-T USB dongle,
supported by the [rtl-sdr](http://sdr.osmocom.org/trac/wiki/rtl-sdr) project. They cost
$25 US, typically.

Recommended DVB-T dongle vendors include:

* [Hacker Warehouse](http://hackerwarehouse.com/product/dvb-t-usb2-0/)
* [NooElec](http://www.nooelec.com/store/software-defined-radio.html)

If you're looking to do active attacks on TPMS (a topic I haven't explored), I recommend
the [HackRF](https://github.com/mossmann/hackrf/). However, my code has not yet been adapted
to support the HackRF's much wider bandwidth, so you're on your own for the time being.

### Antenna

The antenna that comes with your DVB-T dongle will work well, but you'll get more signal
and less noise with a band-specific antenna.

For 315MHz:
* Linx Technologies [ANT-315-CW-RH-SMA](http://mouser.com/Search/Refine.aspx?Keyword=ANT-315-CW-RH-SMA) 315MHz 51mm (2") helical whip antenna, SMA.
* Linx Technologies [ANT-315-CW-RH](http://mouser.com/Search/Refine.aspx?Keyword=ANT-315-CW-RH) 315MHz 51mm (2") helical whip antenna, RP-SMA.
* Linx Technologies [ANT-315-CW-HWR-SMA](http://mouser.com/Search/Refine.aspx?Keyword=ANT-315-CW-HWR-SMA) 315MHz 142mm (5.6") tilt/swivel whip antenna, SMA.
* Linx Technologies [ANT-315-CW-HWR-RPS](http://mouser.com/Search/Refine.aspx?Keyword=ANT-315-CW-HWR-RPS) 315MHz 142mm (5.6") tilt/swivel whip antenna, RP-SMA.

For 433MHz:
* Linx Technologies [ANT-433-CW-RH-SMA](http://mouser.com/Search/Refine.aspx?Keyword=ANT-433-CW-RH-SMA) 433MHz 51mm (2") helical whip antenna, SMA.
* Linx Technologies [ANT-433-CW-RH](http://mouser.com/Search/Refine.aspx?Keyword=ANT-433-CW-RH) 433MHz 51mm (2") helical whip antenna, RP-SMA.
* Linx Technologies [ANT-433-CW-HWR-SMA](http://mouser.com/Search/Refine.aspx?Keyword=ANT-433-CW-HWR-SMA) 433MHz 142mm (5.6") tilt/swivel whip antenna, SMA.
* Linx Technologies [ANT-433-CW-HWR-RPS](http://mouser.com/Search/Refine.aspx?Keyword=ANT-433-CW-HWR-RPS) 433MHz 142mm (5.6") tilt/swivel whip antenna, RP-SMA.

I'm using the Linx Technologies ANT-315-CW-RH-SMA and ANT-433-CW-RH-SMA with good
results, but you may prefer bigger antennas, or RP-SMA connectors.

Ideally, I'd build a [Yagi-Uda antenna](http://en.wikipedia.org/wiki/Yagi-Uda_antenna). :-)

### Cabling

You'll need a cable to connect the antenna to the DVB-T dongle. The DVB-T dongles
from Hacker Warehouse and NooElec have a female MCX connector. The SMA antennas I
use have a male SMA connector. So you'll want a 50 Ohm cable with a male MCX
connector on one side, and a female SMA connector on the other.

### Filtering

I like to use a SAW filter between the antenna and receiver to further cut noise
and interference. It's certainly not necessary (and likely overkill). The SAW
filter I use is built from a PCB I designed.

# Using

Capture data from a vehicle with a software radio receiver like an RTL-SDR USB
dongle, or a HackRF, or other device capable of capturing approximately 1MHz of
complex spectrum from 315MHz or 433MHz. The best way to constrain packets received
to only one vehicle is to ride in the vehicle as it is driven.

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

# Notes and Things to Investigate

Another CRC reversing package: http://reveng.sourceforge.net

Liquid-DSP library for building efficient software defined radio implementations, perhaps on the HackRF ARM Cortex-M4F: https://github.com/jgaeddert/liquid-dsp

# License

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

# Contact

Jared Boone <jared@sharebrained.com>

ShareBrained Technology, Inc.

<http://www.sharebrained.com/>


The latest version of this repository can be found at
https://github.com/jboone/tpms
