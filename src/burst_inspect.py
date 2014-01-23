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

import yaml

from PySide import QtCore
from PySide import QtGui

from gnuradio import blocks
from gnuradio import gr
from gnuradio import digital

from numpy_block import NumpySource, NumpySink
#from packet import packet_classify

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
	def min(self):
		if self._min is None:
			self._min = numpy.min(self._data)
		return self._min

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

	def __sub__(self, other):
		if isinstance(other, int) or isinstance(other, float):
			return TimeData(self.samples - other, self.sampling_rate)

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

class GenericWaveformView(WaveformView):
	def _data_changed(self):
		if self.data is not None:
			self.setSceneRect(0, self.data.max, self.data.duration, -(self.data.max - self.data.min))
		self._scale_changed()

	def _scale_changed(self):
		if self.data is not None:
			new_size = self.size()
			self.scale(float(self.width()) / self.data.duration, self.height() / -(self.data.max - self.data.min))
			self.translate(0.0, self.height())

class WaveWidget(QtGui.QWidget):
	range_changed = QtCore.Signal(float, float)

	def __init__(self, parent=None):
		super(WaveWidget, self).__init__(parent=parent)

		self._data = None

		self.waveform_view = GenericWaveformView(self)

	def get_data(self):
		return self._data

	def set_data(self, data):
		self._data = data
		if self.data is not None:
			self.waveform_view.data = self.data
			#self.histogram_path.data = data
		else:
			self.waveform_view.data = None
	data = property(get_data, set_data)

	def sizeHint(self):
		return QtCore.QSize(50, 50)

	def resizeEvent(self, event):
		super(WaveWidget, self).resizeEvent(event)
		self.waveform_view.resize(event.size())

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
		if self.data is not None:
			self.waveform_view.data = TimeData(self.data.abs.samples, self.data.sampling_rate)
			#self.histogram_path.data = data
		else:
			self.waveform_view.data = None
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
		if self.data is not None:
			values = numpy.angle(self.data.samples[1:] * numpy.conjugate(self.data.samples[:-1]))



			#print('FM HISTOGRAM: %s' % str(numpy.histogram(values, 100)))
			#count_hi = len([x for x in values if x >= 0.0])
			#count_lo = len(values) - count_hi
			#print('%d %d' % (count_lo, count_hi))

			# hist = numpy.histogram(values, 100)
			# def arg_hz(n):
			#   return (n - 50) / 100.0 * self.data.sampling_rate
			# #print('ARGMAX: %f' % (numpy.argmax(hist[0]) / 100.0))
			# print('ARGSORT: %s' % map(arg_hz, numpy.argsort(hist[0])[::-1]))




			self.waveform_view.data = TimeData(values, self.data.sampling_rate)
			#self.histogram_path.data = data
		else:
			self.waveform_view.data = None
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

# def classify_burst(data):
#   return packet_classify(data.samples, data.sampling_rate)
	
# def estimate_fsk_carrier(data):
#   spectrum = numpy.fft.fftshift(numpy.fft.fft(data.samples))
#   mag_spectrum = numpy.log(numpy.absolute(spectrum))
#   argsort = numpy.argsort(mag_spectrum)[::-1]

#   def argsort_hz(n):
#       return ((n / float(len(mag_spectrum))) - 0.5) * data.sampling_rate

#   argsort_peak1_n = argsort[0]

#   n_delta_min = 10e3 / data.sampling_rate * len(mag_spectrum)
#   argsort_2nd = [n for n in argsort[:10] if abs(n - argsort_peak1_n) > n_delta_min]
#   if len(argsort_2nd) > 0:
#       argsort_peak2_n = argsort_2nd[0]

#       shift = argsort_hz((argsort_peak1_n + argsort_peak2_n) / 2.0)
#       return (shift, abs(argsort_hz(argsort_peak2_n) - argsort_hz(argsort_peak1_n)))
#   else:
#       return (0.0, None)

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
		if self.burst is not None:
			windowed_samples = self.burst.samples * scipy.signal.hanning(len(self.burst.samples))
			spectrum = numpy.fft.fftshift(numpy.fft.fft(windowed_samples))
			self._mag_spectrum = numpy.log(numpy.absolute(spectrum))
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
	path_glob = os.path.join(path, 'file*.dat')
	#path_glob = os.path.join(path, '*.cfile')
	filenames = glob.glob(path_glob)
	filenames = sorted(filenames, key=lambda s: int(s.split('_')[1]))
	return filenames

def translate_burst(burst, new_frequency):
	if burst is None:
		return None
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
		#self.slider.setTracking(false)
		self.slider.setSliderPosition(int(round(float(new_value) / self._increment)))
		#self.slider.setTracking(true)

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

class ASKData(QtCore.QObject):
	channel_bandwidth_changed = QtCore.Signal(float)

	def __init__(self):
		super(ASKData, self).__init__()
		self._channel_bandwidth = 10000

	@property
	def channel_bandwidth(self):
		return self._channel_bandwidth

	@channel_bandwidth.setter
	def channel_bandwidth(self, new_value):
		self._channel_bandwidth = new_value
		self.channel_bandwidth_changed.emit(self._channel_bandwidth)

class FSKData(QtCore.QObject):
	deviation_changed = QtCore.Signal(float)

	def __init__(self):
		super(FSKData, self).__init__()
		self._deviation = 38400

	@property
	def deviation(self):
		return self._deviation

	@deviation.setter
	def deviation(self, new_value):
		self._deviation = new_value
		self.deviation_changed.emit(self._deviation)

class Burst(QtCore.QObject):
	symbol_rate_changed = QtCore.Signal(float)
	center_frequency_changed = QtCore.Signal(float)
	modulation_changed = QtCore.Signal(str)

	raw_changed = QtCore.Signal(object)
	translated_changed = QtCore.Signal(object)
	filtered_changed = QtCore.Signal(object)

	def __init__(self):
		super(Burst, self).__init__()
		self._symbol_rate = 19200
		self._center_frequency = 0
		self._modulation = 'fsk'
		self._raw = None
		self._translated = None
		self._filtered = None

	@property
	def symbol_rate(self):
		return self._symbol_rate

	@symbol_rate.setter
	def symbol_rate(self, new_value):
		self._symbol_rate = new_value
		self.symbol_rate_changed.emit(self._symbol_rate)
	
	@property
	def center_frequency(self):
		return self._center_frequency

	@center_frequency.setter
	def center_frequency(self, new_value):
		self._center_frequency = new_value
		self.center_frequency_changed.emit(self._center_frequency)
	
	@property
	def modulation(self):
		return self._modulation

	@modulation.setter
	def modulation(self, new_value):
		self._modulation = new_value
		self.modulation_changed.emit(self._modulation)
	
	@property
	def raw(self):
		return self._raw

	@raw.setter
	def raw(self, new_value):
		self._raw = new_value
		self.raw_changed.emit(self._raw)

	@property
	def translated(self):
		return self._translated

	@translated.setter
	def translated(self, new_value):
		self._translated = new_value
		self.translated_changed.emit(self._translated)

	@property
	def filtered(self):
		return self._filtered

	@filtered.setter
	def filtered(self, new_value):
		self._filtered = new_value
		self.filtered_changed.emit(self._filtered)

class ASKWidget(QtGui.QWidget):
	def __init__(self, burst, parent=None):
		super(ASKWidget, self).__init__(parent)

		self._taps = None

		self.burst = burst
		self.burst.translated_changed[object].connect(self.translated_changed)

		self.modulation = ASKData()
		self.modulation.channel_bandwidth_changed[float].connect(self.channel_bandwidth_changed)

		self.filtered_view = WaveWidget(self)

		self.channel_bandwidth_slider = Slider("Channel BW", 2.5e3, 25e3, 100, self.modulation.channel_bandwidth, self)
		self.channel_bandwidth_slider.value_changed[float].connect(self.channel_bandwidth_slider_changed)

		self.views_layout = QtGui.QGridLayout()
		self.views_layout.setContentsMargins(0, 0, 0, 0)
		self.views_layout.addWidget(self.channel_bandwidth_slider, 0, 0)
		self.views_layout.addWidget(self.filtered_view, 1, 0)
		self.setLayout(self.views_layout)

	def channel_bandwidth_slider_changed(self, value):
		self.modulation.channel_bandwidth = value

	def channel_bandwidth_changed(self, value):
		self.channel_bandwidth_slider.value = value
		self._update_filter(self.burst.translated)

	def translated_changed(self, translated):
		self._update_filtered(translated)

	def _update_filter(self, translated):
		if translated is not None:
			bands = (0, self.modulation.channel_bandwidth * 0.5, self.modulation.channel_bandwidth * 0.6, translated.sampling_rate * 0.5)
			gains = (1.0, 0.0)
			self._taps = scipy.signal.remez(257, bands, gains, Hz=translated.sampling_rate)
		else:
			self._taps = None
		self._update_filtered(translated)

	def _update_filtered(self, translated):
		if translated is not None and self._taps is not None:
			filtered = TimeData(numpy.complex64(scipy.signal.lfilter(self._taps, 1, translated.samples)), translated.sampling_rate)
			filtered_abs = filtered.abs

			data_source = filtered_abs.samples
			numpy_source = NumpySource(data_source)
			peak_detector = blocks.peak_detector_fb(1.0, 0.3, 10, 0.001)
			sample_and_hold = blocks.sample_and_hold_ff()
			multiply_const = blocks.multiply_const_vff((0.5, ))
			subtract = blocks.sub_ff(1)
			numpy_sink = NumpySink(numpy.float32)
			top = gr.top_block()
			top.connect((numpy_source, 0), (peak_detector, 0))
			top.connect((numpy_source, 0), (sample_and_hold, 0))
			top.connect((numpy_source, 0), (subtract, 0))
			top.connect((peak_detector, 0), (sample_and_hold, 1))
			top.connect((sample_and_hold, 0), (multiply_const, 0))
			top.connect((multiply_const, 0), (subtract, 1))
			top.connect((subtract, 0), (numpy_sink, 0))
			top.run()
			filtered = TimeData(numpy_sink.data, translated.sampling_rate)

			self.filtered_view.data = filtered
			# abs_min = filtered.abs.min
			# abs_max = filtered.abs.max
			# abs_mid = (abs_min + abs_max) / 2.0

			# self.burst.filtered = filtered.abs - abs_mid
			self.burst.filtered = filtered
		else:
			self.filtered_view.data = None
			self.burst.filtered = None

class FSKWidget(QtGui.QWidget):
	def __init__(self, burst, parent=None):
		super(FSKWidget, self).__init__(parent)

		self._taps_p = None
		self._taps_n = None

		self.burst = burst
		self.burst.symbol_rate_changed[float].connect(self.symbol_rate_changed)
		self.burst.translated_changed[object].connect(self.translated_changed)

		self.modulation = FSKData()
		self.modulation.deviation_changed[float].connect(self.deviation_changed)

		self.eye_view = EyeWidget(self)

		self.deviation_slider = Slider("Deviation", 5e3, 50e3, 100, self.modulation.deviation, self)
		self.deviation_slider.value_changed[float].connect(self.deviation_slider_changed)

		self.views_layout = QtGui.QGridLayout()
		self.views_layout.setContentsMargins(0, 0, 0, 0)
		self.views_layout.addWidget(self.deviation_slider, 0, 0)
		self.views_layout.addWidget(self.eye_view, 1, 0)
		self.setLayout(self.views_layout)

	def translated_changed(self, translated):
		if self.isVisible():
			self._update_filtered(translated)

	def deviation_slider_changed(self, value):
		self.modulation.deviation = value

	def symbol_rate_changed(self, value):
		if self.isVisible():
			self._update_filter(self.burst.translated)

	def deviation_changed(self, value):
		self.deviation_slider.value = value
		self._update_filter(self.burst.translated)

	def _update_filter(self, translated):
		if translated is not None:
			samples_per_symbol = translated.sampling_rate / self.burst.symbol_rate
			tap_count = int(math.floor(samples_per_symbol))
			x = numpy.arange(tap_count, dtype=numpy.float32) * 2.0j * numpy.pi / translated.sampling_rate
			self._taps_n = numpy.exp(x * -self.modulation.deviation)
			self._taps_p = numpy.exp(x *  self.modulation.deviation)
		else:
			self._taps_n = None
			self._taps_p = None
		self._update_filtered(translated)

	def _update_filtered(self, translated):
		if translated is not None and self._taps_n is not None and self._taps_p is not None:
			filtered_data_1 = TimeData(numpy.complex64(scipy.signal.lfilter(self._taps_n, 1, translated.samples)), translated.sampling_rate)
			filtered_data_2 = TimeData(numpy.complex64(scipy.signal.lfilter(self._taps_p, 1, translated.samples)), translated.sampling_rate)
			self.eye_view.data = (filtered_data_1.abs, filtered_data_2.abs)
			self.burst.filtered = TimeData(filtered_data_2.abs.samples - filtered_data_1.abs.samples, filtered_data_1.sampling_rate)
		else:
			self.eye_view.data = (None, None)
			self.burst.filtered = None

class Browser(QtGui.QWidget):
	def __init__(self, path, parent=None):
		super(Browser, self).__init__(parent)
		self.setGeometry(0, 0, 1500, 700)

		self.burst = Burst()
		self.burst.symbol_rate_changed[float].connect(self.symbol_rate_changed)
		self.burst.raw_changed[object].connect(self.raw_changed)
		self.burst.filtered_changed[object].connect(self.filtered_changed)

		self.file_path = None

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

		self.modulation_tabs = QtGui.QTabWidget()
		self.modulation_tabs.currentChanged[int].connect(self.modulation_tab_changed)
		self.tab_ask = ASKWidget(self.burst)
		self.modulation_tabs.addTab(self.tab_ask, "ASK")
		self.tab_fsk = FSKWidget(self.burst)
		self.modulation_tabs.addTab(self.tab_fsk, "FSK")
		self.modulation_tabs.setCurrentWidget(self.tab_fsk)

		self.translation_frequency_slider = Slider("F Shift", -200e3, 200e3, 1e3, self.burst.center_frequency, self)
		self.translation_frequency_slider.value_changed[float].connect(self.translation_frequency_slider_changed)

		self.symbol_rate_slider = Slider("Symbol Rate", 5e3, 25e3, 10, self.burst.symbol_rate, self)
		self.symbol_rate_slider.value_changed[float].connect(self.symbol_rate_slider_changed)

		self.slicer_view = SlicerWidget(self)
		self.sliced_view = SlicerWidget(self)

		self._gain_mu = 0.2
		self._gain_omega = 0.25 * self._gain_mu * self._gain_mu
		self._omega_relative_limit = 0.001

		self.views_layout = QtGui.QGridLayout()
		self.views_layout.setContentsMargins(0, 0, 0, 0)
		self.views_layout.addWidget(self.am_view, 0, 0)
		self.views_layout.addWidget(self.fm_view, 1, 0)
		self.views_layout.addWidget(self.spectrum_view, 2, 0)
		self.views_layout.addWidget(self.translation_frequency_slider, 3, 0)
		self.views_layout.addWidget(self.modulation_tabs, 4, 0)
		self.views_layout.addWidget(self.symbol_rate_slider, 5, 0)
		self.views_layout.addWidget(self.slicer_view, 6, 0)
		self.views_layout.addWidget(self.sliced_view, 7, 0)
		self.views_layout.setRowStretch(0, 0)
		self.views_layout.setRowStretch(1, 0)
		self.views_layout.setRowStretch(2, 0)
		self.views_layout.setRowStretch(3, 0)
		self.views_layout.setRowStretch(4, 0)
		self.views_layout.setRowStretch(5, 0)
		self.views_layout.setRowStretch(6, 0)
		self.views_layout.setRowStretch(7, 0)
		self.views_layout.setRowStretch(8, 1)
		self.views_widget.setLayout(self.views_layout)

		self.top_layout = QtGui.QVBoxLayout()
		self.top_layout.addWidget(self.splitter)

		self.setLayout(self.top_layout)

	def modulation_tab_changed(self, tab_index):
		modulation_tab = self.modulation_tabs.widget(tab_index)
		if modulation_tab == self.tab_ask:
			self.burst.modulation = 'ask'
		elif modulation_tab == self.tab_fsk:
			self.burst.modulation = 'fsk'
		else:
			self.burst.modulation = None

	def symbol_rate_changed(self, value):
		self.symbol_rate_slider.value = value
		self._update_sliced(self.burst.filtered)

	def symbol_rate_slider_changed(self, value):
		self.burst.symbol_rate = value

	def range_changed(self, start_time, end_time):
		print('%f %f' % (start_time, end_time))
		start_sample = int(start_time * self.burst.raw.sampling_rate)
		end_sample = int(end_time * self.burst.raw.sampling_rate)
		self.burst.translated = TimeData(self.burst.raw.samples[start_sample:end_sample], self.burst.raw.sampling_rate)
		self.spectrum_view.burst = self.burst.translated

	def shift_translation_frequency(self, frequency_shift):
		new_frequency = self.burst.center_frequency + frequency_shift
		sampling_rate = self.burst.raw.sampling_rate
		nyquist_frequency = sampling_rate / 2.0
		while new_frequency < -nyquist_frequency:
			new_frequency += sampling_rate
		while new_frequency >= nyquist_frequency:
			new_frequency -= sampling_rate
		return new_frequency

	def translation_frequency_changing(self, frequency_shift):
		new_frequency = self.shift_translation_frequency(frequency_shift)
		self.burst.translated = translate_burst(self.burst.raw, new_frequency)
		self.spectrum_view.burst = self.burst.translated

	def translation_frequency_changed(self, frequency_shift):
		self.burst.center_frequency = self.shift_translation_frequency(frequency_shift)
		self.translation_frequency_slider.value = self.burst.center_frequency
		self._update_translation(self.burst.raw)

	def translation_frequency_slider_changed(self, translation_frequency):
		self.burst.center_frequency = translation_frequency
		self._update_translation(self.burst.raw)

	def raw_changed(self, data):
		self.am_view.data = self.burst.raw
		self.fm_view.data = self.burst.raw
		self._update_translation(data)

	def filtered_changed(self, data):
		self._update_sliced(data)

	# carrier_frequency, spread_frequency = estimate_fsk_carrier(self._burst)
	#burst_characteristics = classify_burst(self._burst)

	#self._translation_frequency = -burst_characteristics['carrier']
	#if burst_characteristics['modulation'] == 'fsk':
	#   self.deviation_slider.value = burst_characteristics['deviation']

	@property
	def metadata_filename(self):
		if self.file_path:
			file_basename, file_extension = os.path.splitext(self.file_path)
			return '%s%s' % (file_basename, '.yaml')
		else:
			return None

	def _update_yaml(self):
		if self.metadata_filename:
			data = {
				'symbol_rate': self.burst.symbol_rate,
				'modulation': {
					'type': self.burst.modulation,
				},
				'center_frequency': self.burst.center_frequency,
			}
			if self.burst.modulation == 'ask':
				data['modulation']['channel_bandwidth'] = self.tab_ask.modulation.channel_bandwidth
			if self.burst.modulation == 'fsk':
				data['modulation']['deviation'] = self.tab_fsk.modulation.deviation
			data_yaml = yaml.dump(data)
			f_yaml = open(self.metadata_filename, 'w')
			f_yaml.write(data_yaml)
			f_yaml.close()

	def set_file(self, file_path):
		if self.metadata_filename:
			self._update_yaml()

		self.file_path = file_path

		if os.path.exists(self.metadata_filename):
			f_yaml = open(self.metadata_filename, 'r')
			metadata = yaml.load(f_yaml)
			self.burst.symbol_rate = metadata['symbol_rate']
			self.burst.center_frequency = metadata['center_frequency']
			if 'modulation' in metadata:
				modulation = metadata['modulation']
				if modulation['type'] == 'ask':
					self.tab_ask.modulation.channel_bandwidth = modulation['channel_bandwidth']
					self.modulation_tabs.setCurrentWidget(self.tab_ask)
				elif modulation['type'] == 'fsk':
					self.tab_fsk.modulation.deviation = modulation['deviation']
					self.modulation_tabs.setCurrentWidget(self.tab_fsk)

		data = numpy.fromfile(file_path, dtype=numpy.complex64)
		sampling_rate = 400e3
		self.burst.raw = TimeData(data, sampling_rate)

	def delete_file(self, file_path):
		file_base, file_ext = os.path.splitext(file_path)
		file_glob = '%s%s' % (file_base, '.*')
		for matched_file_path in glob.glob(file_glob):
			os.remove(matched_file_path)

	def _update_translation(self, raw_data):
		self.burst.translated = translate_burst(raw_data, self.burst.center_frequency)
		self.spectrum_view.burst = self.burst.translated

	def _update_sliced(self, filtered_symbols):
		self.slicer_view.data = filtered_symbols

		if filtered_symbols is None:
			self.sliced_view.data = None
			return

		omega = float(filtered_symbols.sampling_rate) / self.burst.symbol_rate
		mu = 0.5

		data_source = filtered_symbols.samples
		numpy_source = NumpySource(data_source)
		clock_recovery = digital.clock_recovery_mm_ff(omega, self._gain_omega, mu, self._gain_mu, self._omega_relative_limit)
		numpy_sink = NumpySink(numpy.float32)
		top = gr.top_block()
		top.connect(numpy_source, clock_recovery)
		top.connect(clock_recovery, numpy_sink)
		top.run()
		symbol_data = numpy_sink.data

		# TODO: Adjust sampling rate
		bits = []
		for i in range(len(symbol_data)):
			if symbol_data[i] >= 0:
				symbol_data[i] = 1
				bits.append('1')
			else:
				symbol_data[i] = -1
				bits.append('0')
		bits = ''.join(bits)
		#print(bits)

		self.sliced_view.data = TimeData(symbol_data, self.burst.symbol_rate)

if __name__ == '__main__':
	app = QtGui.QApplication(sys.argv)

	browser = Browser(sys.argv[1])
	browser.show()

	sys.exit(app.exec_())
