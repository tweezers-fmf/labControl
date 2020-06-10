import socket
from labControl.tweezers.conf import ERRORLIST, LOGLEVEL  # TODO: change back to .conf
from labtools.log import create_logger

logger = create_logger(__name__, LOGLEVEL)


class Tweezer:

    def __init__(self, host, port):
        self.host = host
        self.port = port
        pass

    def _query(self, order='', bufferSize=1024):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            logger.debug(f'Sending command "{order}".')
            s.send(f'{order}\r\n'.encode())

            echo = s.recv(bufferSize).decode().strip()
            logger.debug(f'Received error: "{echo}"')
        return echo


class Optical(Tweezer):

    def __init__(self, host='88.200.77.138', port=2070):
        super().__init__(host, port)

        # test connection
        connTest = self._query('test')
        if not connTest == '1':
            logger.warn(f'Got {connTest} instead of "1".')

    def query(self, order='', bufferSize=1024):
        return ERRORLIST(self._query(order, bufferSize))

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

class Magnetic(Tweezer):
    DIR = {
        'x':(0, 1),
        'y':(6, 7),
        'z':(4, 5)
    }

    def __init__(self, host='88.200.78.109', port=2222):
        super().__init__(host, port)

        # test connection
        connTest = self.query('test')
        logger.info(f'Tested connection on {self.host}:{self.port}. Response = {connTest}')

    def query(self, order='', bufferSize=1024):
        return self._query(order, bufferSize)

    def synchronize(self):
        return self.query('synchronize')

    def reset(self):
        return self.query('reset')

    def disable(self, direction='x'):
        dirs = self.DIR[direction]

        r1 = self.query(f'disable {dirs[0]}')
        r2 = self.query(f'disable {dirs[1]}')

        return r1, r2

    def setDC(self, direction='x'):
        dirs = self.DIR[direction]

        r1 = self.query(f'setdc {dirs[0]}')
        r2 = self.query(f'setdc {dirs[1]}')

        return r1, r2

    def setDCAmplitude(self, direction='x', amplitude=0.):
        dirs = self.DIR[direction]

        r1 = self.query(f'dc_value {dirs[0]} {amplitude}')
        r2 = self.query(f'dc_value {dirs[1]} {amplitude}')

        return r1, r2

    def setWaveform(self, direction='x'):
        dirs = self.DIR[direction]

        r1 = self.query(f'waveform {dirs[0]}')
        r2 = self.query(f'waveform {dirs[1]}')

        return r1, r2

    def setFrequency(self, direction='x', frequency=0.):
        dirs = self.DIR[direction]

        r1 = self.query(f'setfreq {dirs[0]} {frequency}')
        r2 = self.query(f'setfreq {dirs[1]} {frequency}')

        return r1, r2

    def setAmplitude(self, direction='x', amplitude=0.):
        dirs = self.DIR[direction]

        r1 = self.query(f'scale {dirs[0]} {amplitude}')
        r2 = self.query(f'scale {dirs[1]} {amplitude}')

        return r1, r2

    def setPhase(self, direction='x', phase=0., shift=180.):
        dirs = self.DIR[direction]
        if phase+shift > 360:
            shift -= 360

        r1 = self.query(f'scale {dirs[0]} {phase}')
        r2 = self.query(f'scale {dirs[1]} {phase+shift}')

        return r1, r2



if __name__ == '__main__':
    from labControl import timing

    test = Magnetic()

    timing.sleep(2)

    test.setDC()

