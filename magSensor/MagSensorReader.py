"""
.. module:: magneticSensor
   :synopsis: Magnetic sensor reader

.. moduleauthor:: Ziga Gregorin <ziga.gregorin@gmail.com>

Data reader for Arduino controlled magnetic field sensor

"""
__author__ = 'Ziga Gregorin'

import time
import numpy as np
from serial.serialutil import SerialException

from labtools.log import create_logger
from labtools.utils.instr import BaseDevice, InstrError, process_if_initialized
from .conf import TIMEOUT, LOGLEVEL, SIMULATE, BAUDRATE

if SIMULATE:
    from labtools.pi._test.serial_test import Serial, comports
else:
    from serial import Serial
    from serial.tools.list_ports import comports

logger = create_logger(__name__, LOGLEVEL)


def findPort():
    """
	Scans all serial ports for first two lines. It returns serial port name
	if it returns "Hello" and "init"

	Returns
	-------

	port : str
		Port name or None if none are found

	Examples
	--------

	>>> findPort()
	'COM7'
	"""
    for portdesc in comports():
        port, desc, dev = portdesc
        s = Serial(timeout=TIMEOUT, baudrate=BAUDRATE)
        try:
            s.port = port
            s.open()
        except SerialException:
            logger.info('Could not open port {}'.format(port))
        else:
            if _checkPort(s):
                return port
        finally:
            s.close()
    logger.warn('Could not find any port')


def _checkPort(serial):
    logger.info('Checkinig port {} for init lines.'.format(serial.port))
    time.sleep(1)  # timeout 1 second

    line1 = serial.readline().strip()
    line2 = serial.readline().strip()

    if line1 == b'Hello' and line2 == b'init':
        logger.debug('Sensor found on port {}'.format(serial.port))
        return True
    else:
        logger.debug('Got {} instead of "Hello" and {} instead of "init" on port {}.'.format(line1, line2, serial.port))
        return False


def _serial_default():
    return Serial(timeout=TIMEOUT, baudrate=BAUDRATE)


class Magsensor(BaseDevice):
    """
	Sensor for reading magnetic field in (x,y,z)
	"""

    def __init__(self, serial=None):
        self._initialized = False
        if serial is not None:
            self.serial = serial
        else:
            self.serial = _serial_default()

    def init(self, port=None, baudrate=None):
        """Opens connection to a device. If port is not given and serial has
        not yet been configured, it will automatically open a valid port.

		:param port: str
			port number or None for default (search for port)
		:param baudrate: int
		"""
        logger.info('Initializing Magsensor.')
        self._initialized = False
        self._info = 'Unknown'
        if baudrate is not None:
            self.serial.baudrate = baudrate
        if port is not None:
            self.serial.port = port
            if not self.serial.is_open:
                self.serial.open()
            if not _checkPort(self.serial):
                # if self.serial does not meet requrements
                raise InstrError('Port {} does not meet requirements.'.format(self.serial.port))
        else:
            port = findPort()
            if port is None:
                raise InstrError('Sensor not found in any port.')
            self.serial.port = port
            self.serial.open()
            if not _checkPort(self.serial):
                # if self.serial does not meet requrements
                raise InstrError('Port {} does not meet requirements in second init.'.format(self.serial.port))
        self._info = 'MicroteslaSensor by Natan Osterman'
        self._initialized = True

    @process_if_initialized
    def readData(self, nAvg=1, sigmaQ=False):
        """ Flushes input and reads lines of data. Averages over nAvg

        :param nAvg: int
            number of averages
        :param sigmaQ: bool
            return sigma
        :return: ndarray
            magnetic field in micro tesla
        """
        x, y, z = _read(self.serial)
        tab = np.array([[x, y, z]])

        for i in range(nAvg - 1):
            x, y, z = _read(self.serial, flushQ=False)
            tab = np.append(tab, [[x, y, z]], axis=0)

        if sigmaQ:
            return np.concatenate((tab.mean(axis=0), tab.std(axis=0)))
        return np.mean(tab, axis=0)

    @process_if_initialized
    def readTimeAndData(self, nAvg=1, sigmaQ=False):
        """ Flushes input and reads lines of data. Averages over nAvg

		:param nAvg: int
			number of averages
		:param sigmaQ: bool
			return sigma
		:return: ndarray
			magnetic field in micro tesla
		"""
        tab = np.empty((0, 3))
        t0 = time.time()

        for i in range(nAvg):
            x, y, z = _read(self.serial, flushQ=False)
            tab = np.append(tab, [[x, y, z]], axis=0)
        t1 = time.time()

        if sigmaQ:
            return (t0 + t1) / 2, np.concatenate((tab.mean(axis=0), tab.std(axis=0)))
        return (t0 + t1) / 2, np.mean(tab, axis=0)

    def close(self):
        """Closes connection to the device
		"""
        logger.info('Closing port {}'.format(self.serial.port))
        self._initialized = False
        self._info = 'Unknown'
        self.serial.close()

    def __del__(self):
        self.close()


def _flush(serial):
    """
	Flushes serial input
	"""
    logger.debug('Flushing serial input on port {}'.format(serial.port))
    serial.reset_input_buffer()


def _read(serial, flushQ=True):
    """
	Flushes serial input and reads one line of data

	:return: float x, float y, float z
		magnetic field in micro tesla
	"""
    if flushQ:
        _flush(serial)

    logger.debug('Reading output from serial port %s' % serial.port)
    t = serial.readline()
    try:
        return _formatInput(t)
    except InstrError:
        logger.warn('Not able to split input "{}".'.format(t))
        return _read(serial, flushQ=False)


def _formatInput(line):
    """
	Formats input to get Bx, By, Bz
	:param line: string line
	:return: float Bx, float By, float Bz or None
	"""
    logger.debug('Formatting output {}'.format(line))
    line = line.split(b'(')[-1]
    line = line.split(b')')[0]
    try:
        x, y, z = [float(k.decode()) for k in line.split()]
        return x, y, z
    except ValueError:
        raise InstrError('Not able to split input "{}".'.format(line))

# if __name__ == '__main__':
# 	m = Magsensor()
# 	m.init()
