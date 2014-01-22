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
import glob
import os
import os.path

import numpy
import scipy.signal

from PySide import QtCore
from PySide import QtGui

from gnuradio import gr
from gnuradio import digital

from numpy_block import NumpySource, NumpySink
from packet import packet_classify

class TimeData(object):
	def __init__(self, data, sampling_rate):
		self._data = data
		self._sampling_rate = sampling_rate
		self._min = None
		self._max = None
		self._abs = None
		self._abs_max = None

	@property
	def sample_count(self):
		return len(self._data)

	@property
	def sampling_rate(self):
		return self._sampling_rate

	@property
	def sampling_interval(self):
		return 1.0 / self.sampling_rate

	@property
	def duration(self):
		return float(self.sample_count) / self.sampling_rate

	@property
	def samples(self):
		return self._data

	@property
	def max(self):
		if self._max is None:
			self._max = numpy.max(self._data)
		return self._max

	@property
	def abs(self):
		if self._abs is None:
			self._abs = numpy.absolute(self._data)
		return TimeData(self._abs, self.sampling_rate)

	@property
	def abs_max(self):
		if self._abs_max is None:
			self._abs_max = numpy.max(self.abs.samples)
		return self._abs_max

# class Burst(object):
# 	def __init__(self, data, sampling_rate):
# 		self._data = data
# 		self._sampling_rate = sampling_rate

# 		#self._mag_time = numpy.absolute(self._data)
# 		#self._frequency_time = numpy.angle(self._data[1:] * numpy.conjugate(self._data[:-1]))
# 		self._mag_spectrum = None

# 	@property
# 	def sample_count(self):
# 		return len(self._data)

# 	@property
# 	def sampling_rate(self):
# 		return self._sampling_rate

# 	@property
# 	def duration(self):
# 		return float(self.sample_count) / self.sampling_rate

# 	@property
# 	def time(self):
# 		return TimeData(self._data, self._sampling_rate)

# 	# @property
# 	# def mag_time(self):
# 	# 	return self._mag_time

# 	# @property
# 	# def frequency_time(self):
# 	# 	return self._frequency_time

# 	@property
# 	def mag_spectrum(self):
# 		if self._mag_spectrum is None:
# 			self._mag_spectrum = numpy.log(numpy.absolute(numpy.fft.fftshift(numpy.fft.fft(self._data))))
# 		return self._mag_spectrum

class Handle(QtGui.QGraphicsLineItem):
	class Signals(QtCore.QObject):
		position_changed = QtCore.Signal(float)

	def __init__(self):
		super(Handle, self).__init__()

		self.signals = Handle.Signals()

		pen = QtGui.QPen()
		pen.setColor(QtCore.Qt.yellow)
		pen.setWidth(3)

		self.setPen(pen)
		self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)

	def setHeight(self, value):
		self.setLine(0, 0, 0, value)

	def mouseMoveEvent(self, event):
		super(Handle, self).mouseMoveEvent(event)
		self.setY(0)
		self.signals.position_changed.emit(self.x())

class WaveformItem(QtGui.QGraphicsPathItem):
	def __init__(self):
		super(WaveformItem, self).__init__()

		self._data = None

	@property
	def data(self):
		return self._data

	@data.setter
	def data(self, value):
		self._data = value
		self.setPath(self._generate_path())

	def _generate_path(self):
		path = QtGui.QPainterPath()

		if self.data is not None:
			sampling_interval = self.data.sampling_interval
			path.moveTo(0, 0)
			for i in range(self.data.sample_count):
				x = i * sampling_interval
				y = self.data.samples[i]
				path.lineTo(x, y)
			path.lineTo(self.data.duration, 0)
		return path

class HistogramItem(QtGui.QGraphicsPathItem):
	def __init__(self):
		super(HistogramItem, self).__init__()

		self._data = None
		self._bin_count = None

	@property
	def bin_count(self):
		return self._bin_count

	@bin_count.setter
	def bin_count(self, value):
		self._bin_count = value

	@property
	def data(self):
		return self._data

	@data.setter
	def data(self, value):
		self._data = value
		self.setPath(self._generate_path())

	def _generate_path(self):
		path = QtGui.QPainterPath()

		if self.data is not None:
			histogram = numpy.histogram(self.data, bins=self.bin_count)
			path.moveTo(0, histogram[1][0])
			for i in range(len(histogram[1]) - 1):
				x = histogram[0][i]
				y = (histogram[1][i] + histogram[1][i+1]) / 2.0
				path.lineTo(x, y)
			path.lineTo(0, histogram[1][-1])
		return path

class WaveformView(QtGui.QGraphicsView):
	def __init__(self, parent=None):
		super(WaveformView, self).__init__(parent)
		self.setFrameStyle(QtGui.QFrame.NoFrame)
		self.setBackgroundBrush(QtCore.Qt.black)
		self.setMouseTracking(True)
		self.setRenderHint(QtGui.QPainter.Antialiasing)
		self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

		self.grabGesture(QtCore.Qt.GestureType.PinchGesture)
		#self.grabGesture(QtCore.Qt.GestureType.PanGesture)

		#self.dragMode = QtGui.QGraphicsView.ScrollHandDrag
		#self.dragMode = QtGui.QGraphicsView.RubberBandDrag
		#self.interactive = True

		#self.resizeAnchor = QtGui.QGraphicsView.AnchorUnderMouse
		#self.transformationAnchor = QtGui.QGraphicsView.AnchorUnderMouse
		#self.viewportAnchor = QtGui.QGraphicsView.AnchorUnderMouse
		self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)

		self.scene = QtGui.QGraphicsScene()
		self.setScene(self.scene)

		color_data = QtGui.QColor(0, 255, 0)
		pen_data = QtGui.QPen(color_data)
		self.data_path = WaveformItem()
		self.data_path.setPen(pen_data)
		self.scene.addItem(self.data_path)

	@property
	def data(self):
		return self.data_path.data

	@data.setter
	def data(self, value):
		self.data_path.data = value
		self.resetTransform()
		self._data_changed()

	def posXToTime(self, x):
		return float(self.mapToScene(x, 0).x()) #* self.data.sampling_interval

	def mouseMoveEvent(self, event):
		t_ms = self.posXToTime(event.x()) * 1000.0
		QtGui.QToolTip.showText(event.globalPos(), '%.2f ms' % (t_ms,))
		return super(WaveformView, self).mouseMoveEvent(event)

	def resizeEvent(self, event):
		super(WaveformView, self).resizeEvent(event)
		self.resetTransform()
		self._scale_changed()

	def event(self, evt):
		if evt.type() == QtCore.QEvent.Type.Gesture:
			return self.gestureEvent(evt)
		return super(WaveformView, self).event(evt)

	def gestureEvent(self, event):
		pinch_gesture = event.gesture(QtCore.Qt.GestureType.PinchGesture)
		scale_factor = pinch_gesture.scaleFactor()
		center = pinch_gesture.centerPoint()

		if pinch_gesture.state() == QtCore.Qt.GestureState.GestureStarted:
			self._gesture_start_transform = self.transform()
		elif pinch_gesture.state() == QtCore.Qt.GestureState.GestureFinished:
			pass
		elif pinch_gesture.state() == QtCore.Qt.GestureState.GestureUpdated:
			pass

		self.scale(self._gesture_start_transform.m11() * scale_factor / self.transform().m11(), 1.0)

		return super(WaveformView, self).event(event)

class AMWaveformView(WaveformView):
	def _data_changed(self):
		if self.data is not None:
			self.setSceneRect(0, 0, self.data.duration, self.data.abs_max)
		self._scale_changed()

	def _scale_changed(self):
		if self.data is not None:
			new_size = self.size()
			self.scale(float(new_size.width()) / self.data.duration, float(new_size.height()) / -self.data.abs_max)
			self.translate(0.0, new_size.height())
	
class AMWidget(QtGui.QWidget):
	range_changed = QtCore.Signal(float, float)

	def __init__(self, parent=None):
		super(AMWidget, self).__init__(parent=parent)

		self._data = None

		self.waveform_view = AMWaveformView(self)

	def get_data(self):
		return self._data

	def set_data(self, data):
		self._data = data
		self.waveform_view.data = TimeData(self.data.abs.samples, self.data.sampling_rate)
		#self.histogram_path.data = data
	data = property(get_data, set_data)

	def sizeHint(self):
		return QtCore.QSize(50, 50)

	def resizeEvent(self, event):
		super(AMWidget, self).resizeEvent(event)
		self.waveform_view.resize(event.size())

class FMWaveformView(WaveformView):
	def _data_changed(self):
		if self.data is not None:
			self.setSceneRect(0, -numpy.pi, self.data.duration, numpy.pi * 2.0)
		self._scale_changed()

	def _scale_changed(self):
		if self.data is not None:
			new_size = self.size()
			self.scale(float(self.width()) / self.data.duration, self.height() / (numpy.pi * -2.0))
			self.translate(0.0, self.height())

class FMWidget(QtGui.QWidget):
	def __init__(self, parent=None):
		super(FMWidget, self).__init__(parent=parent)

		self._data = None

		self.waveform_view = FMWaveformView(self)

	def get_data(self):
		return self._data

	def set_data(self, data):
		self._data = data
		values = numpy.angle(self.data.samples[1:] * numpy.conjugate(self.data.samples[:-1]))



		#print('FM HISTOGRAM: %s' % str(numpy.histogram(values, 100)))
		#count_hi = len([x for x in values if x >= 0.0])
		#count_lo = len(values) - count_hi
		#print('%d %d' % (count_lo, count_hi))

		# hist = numpy.histogram(values, 100)
		# def arg_hz(n):
		# 	return (n - 50) / 100.0 * self.data.sampling_rate
		# #print('ARGMAX: %f' % (numpy.argmax(hist[0]) / 100.0))
		# print('ARGSORT: %s' % map(arg_hz, numpy.argsort(hist[0])[::-1]))




		self.waveform_view.data = TimeData(values, self.data.sampling_rate)
		#self.histogram_path.data = data
	data = property(get_data, set_data)

	def sizeHint(self):
		return QtCore.QSize(50, 50)

	def resizeEvent(self, event):
		super(FMWidget, self).resizeEvent(event)
		self.waveform_view.resize(event.size())

class EyeView(QtGui.QGraphicsView):
	def __init__(self, parent=None):
		super(EyeView, self).__init__(parent=parent)
		self.setFrameStyle(QtGui.QFrame.NoFrame)
		self.setBackgroundBrush(QtCore.Qt.black)
		self.setMouseTracking(True)
		self.setRenderHint(QtGui.QPainter.Antialiasing)
		self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

		#self.dragMode = QtGui.QGraphicsView.ScrollHandDrag
		#self.dragMode = QtGui.QGraphicsView.RubberBandDrag
		#self.interactive = True

		#self.resizeAnchor = QtGui.QGraphicsView.NoAnchor
		#self.transformationAnchor = QtGui.QGraphicsView.NoAnchor

		self.scene = QtGui.QGraphicsScene()
		self.setScene(self.scene)

		color_1 = QtGui.QColor(0, 255, 0)
		pen_1 = QtGui.QPen(color_1)
		color_2 = QtGui.QColor(255, 255, 0)
		pen_2 = QtGui.QPen(color_2)
		
		self.path_1 = WaveformItem()
		self.path_1.setPen(pen_1)
		self.scene.addItem(self.path_1)
		
		self.path_2 = WaveformItem()
		self.path_2.setPen(pen_2)
		self.scene.addItem(self.path_2)

		self._data_1 = None
		self._data_2 = None

		# TODO: Assert that data_1 and data_2 are compatible? Same sampling rates?

	def posXToTime(self, x):
		return float(self.mapToScene(x, 0).x())

	def mouseMoveEvent(self, event):
		t_ms = self.posXToTime(event.x()) * 1000.0
		QtGui.QToolTip.showText(event.globalPos(), '%.2f ms' % (t_ms,))
		return super(EyeView, self).mouseMoveEvent(event)

	def resizeEvent(self, event):
		super(EyeView, self).resizeEvent(event)
		self.resetTransform()
		self._data_changed()

	def get_data_1(self):
		return self._data_1

	def set_data_1(self, data):
		self._data_1 = data
		self.path_1.data = self._data_1
		#self.histogram_path.data = data
		self.resetTransform()
		self._data_changed()
	data_1 = property(get_data_1, set_data_1)

	def get_data_2(self):
		return self._data_2

	def set_data_2(self, data):
		self._data_2 = data
		self.path_2.data = self._data_2
		#self.histogram_path.data = data
		self.resetTransform()
		self._scale_changed()
	data_2 = property(get_data_2, set_data_2)

	def _data_changed(self):
		if (self.data_1 is not None) and (self.data_2 is not None):
			new_size = self.size()
			abs_max = max(self.data_1.abs_max, self.data_2.abs_max)
			self.setSceneRect(0, 0, self.data_1.duration, abs_max)
		self._scale_changed()

	def _scale_changed(self):
		if (self.data_1 is not None) and (self.data_2 is not None):
			new_size = self.size()
			abs_max = max(self.data_1.abs_max, self.data_2.abs_max)
			self.scale(float(self.width()) / self.data_1.duration, self.height() / -abs_max)
			self.translate(0.0, self.height())

class EyeWidget(QtGui.QWidget):
	def __init__(self, parent=None):
		super(EyeWidget, self).__init__(parent=parent)

		self.eye_view = EyeView(self)

		self._data = None

	def get_data(self):
		return self._data

	def set_data(self, data):
		self._data = data
		self.eye_view.data_1 = data[0]
		self.eye_view.data_2 = data[1]

	data = property(get_data, set_data)

	def sizeHint(self):
		return QtCore.QSize(50, 50)

	def resizeEvent(self, event):
		super(EyeWidget, self).resizeEvent(event)
		self.eye_view.resize(event.size())

class SlicerView(WaveformView):
	def _data_changed(self):
		if self.data is not None:
			self.setSceneRect(0, -self.data.abs_max, self.data.duration, 2.0 * self.data.abs_max)
		self._scale_changed()

	def _scale_changed(self):
		if self.data is not None:
			new_size = self.size()
			self.scale(float(self.width()) / self.data.duration, self.height() / -(2.0 * self.data.abs_max))
			self.translate(0.0, self.height())

class SlicerWidget(QtGui.QWidget):
	def __init__(self, parent=None):
		super(SlicerWidget, self).__init__(parent=parent)
		self.slicer_view = SlicerView(self)
		self._data = None

	def get_data(self):
		return self._data

	def set_data(self, data):
		self._data = data
		self.slicer_view.data = data
	data = property(get_data, set_data)

	def sizeHint(self):
		return QtCore.QSize(50, 50)

	def resizeEvent(self, event):
		super(SlicerWidget, self).resizeEvent(event)
		self.slicer_view.resize(event.size())

def classify_burst(data):
	return packet_classify(data.samples, data.sampling_rate)
	
# def estimate_fsk_carrier(data):
# 	spectrum = numpy.fft.fftshift(numpy.fft.fft(data.samples))
# 	mag_spectrum = numpy.log(numpy.absolute(spectrum))
# 	argsort = numpy.argsort(mag_spectrum)[::-1]

# 	def argsort_hz(n):
# 		return ((n / float(len(mag_spectrum))) - 0.5) * data.sampling_rate

# 	argsort_peak1_n = argsort[0]

# 	n_delta_min = 10e3 / data.sampling_rate * len(mag_spectrum)
# 	argsort_2nd = [n for n in argsort[:10] if abs(n - argsort_peak1_n) > n_delta_min]
# 	if len(argsort_2nd) > 0:
# 		argsort_peak2_n = argsort_2nd[0]

# 		shift = argsort_hz((argsort_peak1_n + argsort_peak2_n) / 2.0)
# 		return (shift, abs(argsort_hz(argsort_peak2_n) - argsort_hz(argsort_peak1_n)))
# 	else:
# 		return (0.0, None)

class SpectrumView(QtGui.QWidget):
	translation_frequency_changing = QtCore.Signal(float)
	translation_frequency_changed = QtCore.Signal(float)

	def __init__(self, parent=None):
		super(SpectrumView, self).__init__(parent)
		self.setMouseTracking(True)

		self._burst = None
		self._drag_x = None
		self._carrier_estimate = 0.0

	@property
	def carrier_estimate(self):
		return self._carrier_estimate

	@property
	def burst(self):
		return self._burst

	@burst.setter
	def burst(self, value):
		self._burst = value
		windowed_samples = self.burst.samples * scipy.signal.hanning(len(self.burst.samples))
		spectrum = numpy.fft.fftshift(numpy.fft.fft(windowed_samples))
		self._mag_spectrum = numpy.log(numpy.absolute(spectrum))




		# min_width = int(math.ceil(5e3 / self.burst.sampling_rate * len(self._mag_spectrum)))
		# cwt = scipy.signal.find_peaks_cwt(self._mag_spectrum, numpy.arange(min_width, min_width*2.0), min_snr=5.0)
		# def arg_hz(n):
		# 	return ((float(n) / len(self._mag_spectrum)) - 0.5) * self.burst.sampling_rate
		# print('CWT: %s' % str(map(arg_hz, cwt)))



		self._burst_max = max(self._mag_spectrum)
		self.update()

	def paintEvent(self, event):
		painter = QtGui.QPainter()
		painter.begin(self)
		painter.fillRect(self.rect(), QtCore.Qt.black)

		painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
		if self.burst is not None:
			#painter.setPen(QtCore.Qt.green)
			path = QtGui.QPainterPath()
			path.moveTo(0, 0)
			for x in range(len(self._mag_spectrum)):
				y = self._mag_spectrum[x]
				path.lineTo(x, y)
			path.lineTo(len(self._mag_spectrum), 0)

			#if self._drag_x:
			painter.save()
			painter.translate(self.width(), self.height())
			scale_y = float(self.height()) / self._burst_max
			painter.scale(-self.scale_x, -scale_y)
			brush = QtGui.QBrush(QtCore.Qt.red)
			painter.fillPath(path, brush)
			painter.restore()
			
			painter.save()
			painter.translate(0, self.height())
			scale_y = float(self.height()) / self._burst_max
			painter.scale(self.scale_x, -scale_y)
			brush = QtGui.QBrush(QtCore.Qt.green)
			painter.fillPath(path, brush)
			painter.restore()
			
		painter.end()

	@property
	def scale_x(self):
		if self.burst is None:
			return 1.0
		else:
			return float(self.width()) / len(self._mag_spectrum)

	def mousePressEvent(self, event):
		self._drag_x = event.pos().x()
		return super(SpectrumView, self).mousePressEvent(event)

	def _moveDeltaF(self, event):
		delta_x = event.pos().x() - self._drag_x
		delta_f = float(delta_x) / self.width() * self.burst.sampling_rate
		return delta_f

	def mouseMoveEvent(self, event):
		f = (float(event.x()) / self.width() - 0.5) * self.burst.sampling_rate
		QtGui.QToolTip.showText(event.globalPos(), '%.0f Hz' % (f,))
		if event.buttons() and QtCore.Qt.LeftButton:
			self.translation_frequency_changing.emit(self._moveDeltaF(event))
		return super(SpectrumView, self).mouseMoveEvent(event)

	def mouseReleaseEvent(self, event):
		if event.button() == QtCore.Qt.LeftButton:
			self.translation_frequency_changed.emit(self._moveDeltaF(event))
			self._drag_x = None
		return super(SpectrumView, self).mouseReleaseEvent(event)

	def sizeHint(self):
		return QtCore.QSize(50, 50)

def get_cfile_list(path):
	path_glob = os.path.join(path, '*.dat')
	filenames = glob.glob(path_glob)
	return filenames

def translate_burst(burst, new_frequency):
	mix = numpy.arange(burst.sample_count, dtype=numpy.float32) * 2.0j * numpy.pi * new_frequency / burst.sampling_rate
	mix = numpy.exp(mix) * burst.samples
	return TimeData(mix, burst.sampling_rate)

class Slider(QtGui.QWidget):
	value_changed = QtCore.Signal(float)

	def __init__(self, name, low_value, high_value, increment, default_value, parent=None):
		super(Slider, self).__init__(parent=parent)

		self._increment = increment
		low_int = int(math.floor(float(low_value) / increment))
		high_int = int(math.ceil(float(high_value) / increment))

		self.label = QtGui.QLabel(self)
		self.label.setText(name)
		
		self.slider = QtGui.QSlider(QtCore.Qt.Horizontal, self)
		self.slider.setRange(low_int, high_int)
		self.slider.valueChanged[int].connect(self._value_changed)

		self.text = QtGui.QLabel(self)
		self.text.setText(str(self.value))

		self.layout = QtGui.QBoxLayout(QtGui.QBoxLayout.LeftToRight)
		self.layout.addWidget(self.label)
		self.layout.addWidget(self.slider)
		self.layout.addWidget(self.text)

		self.setLayout(self.layout)

		self.value = default_value

	@property
	def value(self):
		return self.slider.sliderPosition() * self._increment

	@value.setter
	def value(self, new_value):
		self.slider.setSliderPosition(int(round(float(new_value) / self._increment)))

	def _value_changed(self, value):
		self.text.setText(str(self.value))
		self.value_changed.emit(self.value)

class QFileListWidget(QtGui.QListWidget):
	file_changed = QtCore.Signal(str)
	file_deleted = QtCore.Signal(str)

	def __init__(self, file_paths, parent=None):
		super(QFileListWidget, self).__init__(parent)

		for file_path in file_paths:
			file_dir, file_name = os.path.split(file_path)
			file_item = QtGui.QListWidgetItem(file_name)
			file_item.setData(32, file_path)
			self.addItem(file_item)
		self.currentItemChanged.connect(self._file_changed)

	def keyPressEvent(self, event):
		if event.matches(QtGui.QKeySequence.Delete):
			self._delete_selected_items()
		super(QFileListWidget, self).keyPressEvent(event)

	def _file_changed(self, selected, deselected):
		file_path = selected.data(32)
		self.file_changed.emit(file_path)

	def _delete_selected_items(self):
		for item in self.selectedItems():
			file_path = item.data(32)
			self.file_deleted.emit(file_path)
			row = self.row(item)
			self.takeItem(row)

class Browser(QtGui.QWidget):
	def __init__(self, path, parent=None):
		super(Browser, self).__init__(parent)
		self.setGeometry(0, 0, 1500, 700)

		file_paths = get_cfile_list(path)
		self.file_list_view = QFileListWidget(file_paths)
		self.file_list_view.file_changed.connect(self.set_file)
		self.file_list_view.file_deleted.connect(self.delete_file)

		self.views_widget = QtGui.QFrame()
		#self.views_widget.setFrameStyle(QtGui.QFrame.NoFrame)
		#self.views_widget.setContentsMargins(0, 0, 0, 0)

		self.splitter = QtGui.QSplitter()
		self.splitter.addWidget(self.file_list_view)
		self.splitter.addWidget(self.views_widget)
		self.splitter.setSizes([200, 0])
		self.splitter.setStretchFactor(0, 0)
		self.splitter.setStretchFactor(1, 1)

		self.am_view = AMWidget(self)
		self.am_view.range_changed.connect(self.range_changed)

		self.fm_view = FMWidget(self)

		self.spectrum_view = SpectrumView()
		self.spectrum_view.translation_frequency_changing.connect(self.translation_frequency_changing)
		self.spectrum_view.translation_frequency_changed.connect(self.translation_frequency_changed)

		self.eye_view = EyeWidget(self)

		self.slicer_view = SlicerWidget(self)
		self.sliced_view = SlicerWidget(self)

		self._translation_frequency = 0.0
		# TODO: Set slider range based on burst sample frequency.
		self.translation_frequency_slider = Slider("F Shift", -200e3, 200e3, 1e3, self._translation_frequency, self)
		self.translation_frequency_slider.value_changed[float].connect(self.translation_frequency_changed_by_slider)

		self._symbol_rate = 10e3
		self.symbol_rate_slider = Slider("Symbol Rate", 5e3, 50e3, 10, self._symbol_rate, self)
		self.symbol_rate_slider.value_changed[float].connect(self.symbol_rate_changed)

		self._deviation = self._symbol_rate * 4.0
		self.deviation_slider = Slider("Deviation", 100, 100e3, 100, self._deviation, self)
		self.deviation_slider.value_changed[float].connect(self.deviation_changed)

		self._gain_mu = 0.2
		# self.gain_mu_slider = Slider("Gain Mu", 0.001, 1.0, 0.001, self._gain_mu, self)
		# self.gain_mu_slider.value_changed[float].connect(self.gain_mu_changed)

		self._gain_omega = 0.25 * self._gain_mu * self._gain_mu
		# self.gain_omega_slider = Slider("Gain Omega", 0.00001, 0.01, 0.00001, self._gain_omega, self)
		# self.gain_omega_slider.value_changed[float].connect(self.gain_omega_changed)

		self._omega_relative_limit = 0.001
		# self.omega_relative_limit_slider = Slider("Omega RL", 0.0001, 0.1, 0.0001, self._omega_relative_limit, self)
		# self.omega_relative_limit_slider.value_changed[float].connect(self.omega_relative_limit_changed)

		self.views_layout = QtGui.QGridLayout()
		self.views_layout.setContentsMargins(0, 0, 0, 0)
		self.views_layout.addWidget(self.am_view, 0, 0)
		self.views_layout.addWidget(self.fm_view, 1, 0)
		self.views_layout.addWidget(self.spectrum_view, 2, 0)
		self.views_layout.addWidget(self.eye_view, 3, 0)
		self.views_layout.addWidget(self.slicer_view, 4, 0)
		self.views_layout.addWidget(self.sliced_view, 5, 0)
		self.views_layout.addWidget(self.translation_frequency_slider, 6, 0)
		self.views_layout.addWidget(self.symbol_rate_slider, 7, 0)
		self.views_layout.addWidget(self.deviation_slider, 8, 0)
		# self.views_layout.addWidget(self.gain_mu_slider, 9, 0)
		# self.views_layout.addWidget(self.gain_omega_slider, 10, 0)
		# self.views_layout.addWidget(self.omega_relative_limit_slider, 11, 0)
		self.views_layout.setRowStretch(0, 0)
		self.views_layout.setRowStretch(1, 0)
		self.views_layout.setRowStretch(2, 0)
		self.views_layout.setRowStretch(3, 0)
		self.views_layout.setRowStretch(4, 0)
		self.views_layout.setRowStretch(5, 0)
		self.views_layout.setRowStretch(6, 0)
		self.views_layout.setRowStretch(7, 0)
		self.views_layout.setRowStretch(8, 0)
		# self.views_layout.setRowStretch(9, 0)
		# self.views_layout.setRowStretch(10, 0)
		# self.views_layout.setRowStretch(11, 0)
		self.views_layout.setRowStretch(12, 1)
		self.views_widget.setLayout(self.views_layout)

		self.top_layout = QtGui.QVBoxLayout()
		self.top_layout.addWidget(self.splitter)

		self.setLayout(self.top_layout)

	def symbol_rate_changed(self, value):
		self._symbol_rate = value
		self._update_data()

	def deviation_changed(self, value):
		self._deviation = value
		self._update_data()

	# def gain_mu_changed(self, value):
	# 	self._gain_mu = value
	# 	self._gain_omega = 0.25 * self._gain_mu * self._gain_mu
	# 	self.gain_omega_slider.value = self._gain_omega
	# 	self._update_data()

	# def gain_omega_changed(self, value):
	# 	self._gain_omega = value
	# 	self._update_data()

	# def omega_relative_limit_changed(self, value):
	# 	self._omega_relative_limit = value
	# 	self._update_data()

	def range_changed(self, start_time, end_time):
		print('%f %f' % (start_time, end_time))
		start_sample = int(start_time * self.burst.sampling_rate)
		end_sample = int(end_time * self.burst.sampling_rate)
		self.spectrum_view.burst = TimeData(self.burst.samples[start_sample:end_sample], self.burst.sampling_rate)

	def shift_translation_frequency(self, frequency_shift):
		new_frequency = self._translation_frequency + frequency_shift
		sampling_rate = self.burst.sampling_rate
		nyquist_frequency = sampling_rate / 2.0
		while new_frequency < -nyquist_frequency:
			new_frequency += sampling_rate
		while new_frequency >= nyquist_frequency:
			new_frequency -= sampling_rate
		return new_frequency

	def translation_frequency_changing(self, frequency_shift):
		new_frequency = self.shift_translation_frequency(frequency_shift)
		self.spectrum_view.burst = translate_burst(self.burst, new_frequency)

	def translation_frequency_changed(self, frequency_shift):
		self._translation_frequency = self.shift_translation_frequency(frequency_shift)
		self.translation_frequency_slider.value = self._translation_frequency
		self._update_data()

	def translation_frequency_changed_by_slider(self, translation_frequency):
		self._translation_frequency = translation_frequency
		self._update_data()

	@property
	def burst(self):
		return self._burst

	@burst.setter
	def burst(self, value):
		self._burst = value

		# carrier_frequency, spread_frequency = estimate_fsk_carrier(self._burst)
		burst_characteristics = classify_burst(self._burst)

		#self._translation_frequency = -burst_characteristics['carrier']
		#if burst_characteristics['modulation'] == 'fsk':
		#	self.deviation_slider.value = burst_characteristics['deviation']

		self._update_data()

	def set_file(self, file_path):
		data = numpy.fromfile(file_path, dtype=numpy.complex64)
		sampling_rate = 400e3
		self.burst = TimeData(data, sampling_rate)

	def delete_file(self, file_path):
		os.remove(file_path)

	def _update_data(self):
		self._update_translation()

	def _update_translation(self):
		translated_burst = translate_burst(self.burst, self._translation_frequency)
		self.spectrum_view.burst = translated_burst
		self.am_view.data = translated_burst
		self.fm_view.data = translated_burst
		self._update_filter(translated_burst)

	def _update_filter(self, translated_burst):
		self._samples_per_symbol = translated_burst.sampling_rate / self._symbol_rate
		tap_count = int(math.floor(self._samples_per_symbol))
		x = numpy.arange(tap_count, dtype=numpy.float32) * 2.0j * numpy.pi / translated_burst.sampling_rate
		self._taps_n = numpy.exp(x * -self._deviation)
		self._taps_p = numpy.exp(x *  self._deviation)
		self._update_filtered(translated_burst)

	def _update_filtered(self, translated_burst):
		filtered_data_1 = TimeData(numpy.complex64(scipy.signal.lfilter(self._taps_n, 1, translated_burst.samples)), translated_burst.sampling_rate)
		filtered_data_2 = TimeData(numpy.complex64(scipy.signal.lfilter(self._taps_p, 1, translated_burst.samples)), translated_burst.sampling_rate)
		self.eye_view.data = (filtered_data_1.abs, filtered_data_2.abs)

		filtered_diff = TimeData(filtered_data_2.abs.samples - filtered_data_1.abs.samples, filtered_data_1.sampling_rate)		
		self.slicer_view.data = filtered_diff
		#print('sliced abs sum: %s' % sum(abs(filtered_diff.samples)))

		omega = self._samples_per_symbol
		mu = 0.5

		data_source = filtered_diff.samples
		numpy_source = NumpySource(data_source)
		clock_recovery = digital.clock_recovery_mm_ff(omega, self._gain_omega, mu, self._gain_mu, self._omega_relative_limit)
		#clock_recovery = digital.pfb_clock_sync_fff(self._samples_per_symbol, 1.0, self._taps)
		numpy_sink = NumpySink(numpy.float32)
		top = gr.top_block()
		top.connect(numpy_source, clock_recovery)
		top.connect(clock_recovery, numpy_sink)
		top.run()
		data_sink = numpy_sink.data

		# TODO: Adjust sampling rate
		bits = []
		for i in range(len(data_sink)):
			if data_sink[i] >= 0:
				data_sink[i] = 1
				bits.append('1')
			else:
				data_sink[i] = -1
				bits.append('0')
		bits = ''.join(bits)
		#print(bits)

		self.sliced_view.data = TimeData(data_sink, filtered_diff.sampling_rate)

if __name__ == '__main__':
	app = QtGui.QApplication(sys.argv)

	browser = Browser(sys.argv[1])
	browser.show()

	sys.exit(app.exec_())

###########################################################################

		# pen_histogram = QtGui.QPen(QtGui.QColor(255, 64, 64, 255))
		# brush_histogram = QtGui.QBrush(QtGui.QColor(255, 0, 0, 192))
		# self.histogram_path = HistogramItem()
		# self.histogram_path.setPen(pen_histogram)
		# self.histogram_path.setBrush(brush_histogram)
		# self.histogram_path.setZValue(200)
		# self.histogram_path.bin_count = 50
		# self.scene.addItem(self.histogram_path)

	# def _update_data_path(self):
	# 	if self.burst is None:
	# 		self.data_path.data = None
	# 	else:
	# 		data = self.burst.time
	# 		data = (range(len(data)), data)
	# 		self.data_path.data = data

	# def _update_data_scale(self):
	# 	if self.burst is None:
	# 		return

	# 	data = self.burst.time
	# 	absmax = max(numpy.absolute(data))
	# 	scale_x = float(self.width()) / len(data)
	# 	scale_y = float(self.height()) / absmax

	# 	transform = QtGui.QTransform()
	# 	if self._bipolar:
	# 		transform.translate(0, self.height() / 2.0)
	# 		transform.scale(scale_x, -scale_y / 2.0)
	# 	else:
	# 		transform.translate(0, self.height())
	# 		transform.scale(scale_x, -scale_y)
	# 	self.data_path.setTransform(transform)

	# def _update_histogram_path(self):
	# 	if self.burst is None:
	# 		self.histogram_path.data = None
	# 	else:
	# 		data = self.burst.time
	# 		data = (range(len(data)), data)
	# 		self.histogram_path.data = data

		# path = QtGui.QPainterPath()
		# path.moveTo(0, data[1][0])
		# for i in range(len(data[0])):
		# 	y = data[1][i]
		# 	x = data[0][i]
		# 	path.lineTo(x, y)
		# path.lineTo(0, data[1][-1])
		# self.histogram_path.setPath(path)

	# def _update_histogram_scale(self):
	# 	path_width = self.histogram_path.path().boundingRect().width()
	# 	scale_y = float(self.height()) / path_width

	# 	transform = QtGui.QTransform()
	# 	transform.scale(10.0, 0.1)
	# 	if self._bipolar:
	# 		#transform.translate(0, self.height() / 2.0)
	# 		pass
	# 	else:
	# 		#transform.translate(0, self.height())
	# 		pass
	# 	#transform.scale(1, -scale_y)
	# 	#transform.scale(scale_y, 1)
	# 	#transform.rotate(-45)
	# 	self.histogram_path.setTransform(transform)

	# def _update_view(self):
	# 	if self.burst is None:
	# 		return

	# 	self._update_data_scale()
	# 	self.histogram_path.bin_count = self.height()

###########################################################################

		# color_transparent = QtGui.QColor(0, 0, 0, 0)
		# null_pen = QtGui.QPen()
		# null_pen.setWidth(0)
		# null_pen.setColor(color_transparent)

		# crop_mask_color = QtGui.QColor(0, 0, 0, 128)
		# crop_mask_brush = QtGui.QBrush(crop_mask_color)

		# select_mask_color = QtGui.QColor(0, 0, 0, 0)
		# select_mask_brush = QtGui.QBrush(select_mask_color)

		# self.head_mask = QtGui.QGraphicsRectItem()
		# self.head_mask.setPen(null_pen)
		# self.head_mask.setBrush(crop_mask_color)
		# self.head_mask.setZValue(100)
		# self.scene.addItem(self.head_mask)

		# self.tail_mask = QtGui.QGraphicsRectItem()
		# self.tail_mask.setPen(null_pen)
		# self.tail_mask.setBrush(crop_mask_color)
		# self.tail_mask.setZValue(100)
		# self.scene.addItem(self.tail_mask)

		# self.select_mask = QtGui.QGraphicsRectItem()
		# self.select_mask.setPen(null_pen)
		# self.select_mask.setBrush(select_mask_brush)
		# self.select_mask.setZValue(100)
		# self.scene.addItem(self.select_mask)

		# self.start_widget = Handle()
		# self.start_widget.signals.position_changed.connect(self.start_changed)
		# self.start_widget.setZValue(300)
		# self.scene.addItem(self.start_widget)

		# self.end_widget = Handle()
		# self.end_widget.signals.position_changed.connect(self.end_changed)
		# self.end_widget.setZValue(300)
		# self.scene.addItem(self.end_widget)

###########################################################################

	# @property
	# def time_data(self):
	# 	return self._time_data

	# @property
	# def histogram_data(self):
	# 	return self._histogram_data

	# def start_changed(self, new_value):
	# 	if self.burst:
	# 		self.start_time = new_value / self.width() * self.burst.duration
	# 		self.range_changed.emit(self.start_time, self.end_time)
	# 		self._update_mask()

	# def end_changed(self, new_value):
	# 	if self.burst:
	# 		self.end_time = new_value / self.width() * self.burst.duration
	# 		self.range_changed.emit(self.start_time, self.end_time)
	# 		self._update_mask()
		
	# def _data_changed(self):
	# 	self.start_time = 0.0
	# 	self.end_time = self.burst.duration
		
	# 	#self._update_data_path()
	# 	#self._update_histogram_path()
	# 	self._update_view()
	# 	self._update_mask()

	# def _update_mask(self):
	# 	if self.burst is None:
	# 		return

	# 	start = self.start_time / self.burst.duration
	# 	end = self.end_time / self.burst.duration

	# 	width = self.width()
	# 	height = self.height()

	# 	start_x = start * width
	# 	end_x = end * width

	# 	self.head_mask.setRect(0, 0, start_x, height)
	# 	self.tail_mask.setRect(end_x, 0, width - end_x, height)
	# 	self.select_mask.setRect(start_x, 0, end_x - start_x, height)

	# 	self.start_widget.setPos(start_x, 0)
	# 	self.start_widget.setHeight(self.height())

	# 	self.end_widget.setPos(end_x, 0)
	# 	self.end_widget.setHeight(self.height())

###########################################################################

# class CFileList(QtCore.QAbstractListModel):
#	def __init__(self):
#		super(CFileList, self).__init__()
#		self._data = self._fetch_data()

#	def _fetch_data(self):
#		return get_cfile_list()
		
#	def rowCount(self, parent):
#		return len(self._data)

#	def data(self, index, role=QtCore.Qt.DisplayRole):
#		if not index.isValid():
#			return None

#		file_name, file_path = self._data[index.row()]
#		if role == QtCore.Qt.DisplayRole:
#			return file_name
#		elif role == QtCore.Qt.DecorationRole:
#			return None

#		return None

###########################################################################

# class TestWidget(QtGui.QWidget):
# 	def __init__(self, parent=None):
# 		super(TestWidget, self).__init__(parent)
# 
# 	def paintEvent(self, event):
# 		painter = QtGui.QPainter()
# 		painter.begin(self)
# 		painter.fillRect(self.rect(), QtCore.Qt.black)
# 		painter.end()
# 
# class TestWindow(QtGui.QWidget):
# 	def __init__(self, parent=None):
# 		super(TestWindow, self).__init__(parent)
# 
# 		left_widget = TestWidget()
# 		right_widget = QtGui.QFrame()
# 
# 		splitter = QtGui.QSplitter()
# 		splitter.addWidget(left_widget)
# 		splitter.addWidget(right_widget)
# 
# 		# item_1 = QtGui.QLabel("Label 1")
# 		# item_2 = QtGui.QLabel("Label 2")
# 		# item_3 = QtGui.QLabel("Label 3")
# 
# 		item_1 = TestWidget()
# 		item_2 = TestWidget()
# 		item_3 = TestWidget()
# 
# 		box_layout = QtGui.QVBoxLayout()
# 		box_layout.addWidget(item_1)
# 		box_layout.addWidget(item_2)
# 		box_layout.addWidget(item_3)
# 		right_widget.setLayout(box_layout)
# 
# 		top_layout = QtGui.QVBoxLayout()
# 		top_layout.addWidget(splitter)
# 
# 		self.setLayout(top_layout)
# 

	#test = TestWindow()
	#test.show()
