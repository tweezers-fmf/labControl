import socket
from labControl.tweezers.conf import ERRORLIST, LOGLEVEL  # TODO: change back to .conf
from labtools.log import create_logger

logger = create_logger(__name__, LOGLEVEL)

class Optical:

    # default gateways
    HOST = '127.0.0.1'
    PORT = 2070

    def __init__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((Optical.HOST, Optical.PORT))
        logger.info(f'Connecting to {Optical.HOST}:{Optical.PORT}')

        # test connection
        connTest = self._query('test')
        if not connTest == 'unknown command':
            logger.warn(f'Got {connTest} instead of "unknown command".')

    def _query(self, order=''):
        logger.debug(f'Sending command "{order}".')
        self.s.send(f'{order}\r\n'.encode())

        echo = self.s.recv(1024).decode().strip()
        logger.debug(f'Received error: "{echo}" - {ERRORLIST[echo]}')
        return ERRORLIST[echo]

    def setRecFile(self, fileName=''):
        return self._query(f'CAMERA_SET_REC_FILE {fileName}')

    def setImgFile(self, fileName=''):
        return self._query(f'CAMERA_SET_IMG_FILE {fileName}')

    def startRecording(self, FMmode=True):
        fm = '_FM' if FMmode else ''
        return self._query(f'CAMERA_REC_START{fm}')

    def stopRecording(self):
        return self._query('CAMERA_REC_STOP')

    def takeImage(self):
        return self._query('CAMERA_IMG_SINGLE')

    def setClock(self, clock_MHz):
        """ Set camera pixel clock in MHz
        """
        return self._query(f'CAMERA_SET_CLOCK {clock_MHz}')

    def setFPS(self, fps=10):
        return self._query(f'CAMERA_SET_FRAME_RATE {fps}')

    def setExposure(self, exposure_ms=200):
        return self._query(f'CAMERA_SET_EXPOSURE {exposure_ms}')

    def setGain(self, gain=1):
        return self._query(f'CAMERA_SET_GAIN {gain}')

    def focus(self, beamFocus=500):
        return self._query(f'BEAM_SET_FOCUS {beamFocus}')

    def laserOn(self):
        return self._query(f'LASER_ON')

    def laserOff(self):
        return self._query(f'LASER_OFF')

    def laserLevel(self, level=0.2):
        return self._query(f'LASER_SET_LEVEL {level}')

    # TODO: add orders from CLEAR_PROJECT on

class Magnetic:

    # default gateway
    HOST = '88.200.78.109'
    PORT = 2222

    def __init__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((Magnetic.HOST, Magnetic.PORT))
        logger.info(f'Connecting to {Magnetic.HOST}:{Magnetic.PORT}')

        # test connection
        connTest = self._query('test')
        print(connTest)
        # if not connTest == 'unknown command':
        #     logger.warn(f'Got {connTest} instead of "unknown command".')

    def _query(self, order=''):
        logger.debug(f'Sending command "{order}".')
        self.s.send(f'{order}\r\n'.encode())

        echo = self.s.recv(1024).decode().strip()
        # logger.debug(f'Received error: "{echo}" - {ERRORLIST[echo]}')
        # return ERRORLIST[echo]
        return echo

    def setDC(self):
        return self._query(f'setdc 0')

if __name__ == '__main__':

    test = Magnetic()
    test.setDC()

