"""
.. module:: rigol
   :synopsis: Rigol function generator DG1022 Z helper function

.. moduleauthor:: Ziga Gregorin <ziga.gregorin@gmail.com>


"""

import visa
from .conf import INSTR, LOGLEVEL, FUNC
from labtools.log import create_logger
from labtools.utils.instr import BaseDevice, InstrError, process_if_initialized

logger = create_logger(__name__, LOGLEVEL)

class Rigol(BaseDevice):
    """
    Class for Rigol function generator
    """

    def __init__(self, instrID=None):
        self._initialized = False
        self.rm = visa.ResourceManager()
        if instrID is not None:
            self.instrID = instrID
        else:
            self.instrID = INSTR


    def init(self):
        """Opens connection to device

        """
        logger.info('Initializing instrument {}'.format(self.instrID))
        self._initialized = False
        self._info = 'Unknown'

        self.instr = self.rm.open_resource(self.instrID)
        self._info = self.instr.query('*IDN?').strip()
        self._initialized = True


    @process_if_initialized
    def _write(self, command=''):
        """ Writes command to device

        :param command: string: command
        :return: bool
        """
        logger.debug('Writting command "{}"'.format(command))

        self.instr.write(command)
        return True


    @process_if_initialized
    def _ask(self, command=''):
        """ Asks for current state of command, adds '?' at the end

        :param command: string: command
        :return:
        """
        logger.debug('Asking for "{}"'.format(command))

        try:
            result = self.instr.query(command+'?')
        except visa.VisaIOError:
            logger.warn('Could not get query for "{}"'.format(command))
            result = 'Error'

        return result.strip()


    def setFunction(self, function='', ch=1):
        """ Set function type on generator

        :param function: string: should bo found in config
        :param ch: int: channel
        :return: bool
        """
        if function in FUNC:
            logger.debug('Set function to {}'.format(function))

            command = ':SOUR{:d}:FUNC {}'.format(ch, FUNC[function])
            self._write(command)
            return True
        else:
            logger.warn('Function "{}" not recognized!'.format(function))
            return False


    def setFrequency(self, frequency=0., ch=1):
        """ Set frequency on desired channel

        :param frequency: float: frequency value
        :param ch: int: channel
        :return: bool
        """
        logger.debug('Set frequency to {:f} Hz'.format(frequency))
        self._write(':SOUR{:d}:FREQ {:f}'.format(ch, frequency))

        return True


    def setVoltage(self, voltage=0., ch=1):
        """ Set amplitude voltage peak-to-peak on desired channel

        :param voltage: float: voltage peak-to-peak
        :param ch: int: channel
        :return: bool
        """
        logger.debug('Set voltage to {:f} Vpp'.format(voltage))
        self._write(':SOUR{:d}:VOLT {:f}'.format(ch, voltage))

        return True


    def setOffset(self, offset=0., ch=1):
        """ Set offset voltage on desired channel

            :param offset: float: offset voltage
            :param ch: int: channel
            :return: bool
            """
        logger.debug('Set offset voltage to {:f} V'.format(offset))
        self._write(':SOUR{:d}:VOLT:OFFS {:f}'.format(ch, offset))

        return True


    def setPhase(self, phase=0., ch=1):
        """ Set phase on desired channel

            :param phase: float: phase in degrees
            :param ch: int: channel
            :return: bool
            """
        logger.debug('Set phase to {:f}°'.format(phase))
        self._write(':SOUR{:d}:PHAS {:f}'.format(ch, phase))

        return True


    def setAll(self, channel=1, function='', frequency=0., voltage=0., offset=0., phase=0.):
        """ Set basic waveform with all parameters

        :param channel: int: channel number
        :param function: string: function from dictionary FUNC
        :param frequency: float: frequency in Hz
        :param voltage: float: amplitude voltage peak-to-peak in V
        :param offset: float: offest voltage in V
        :param phase: float: phase shift in degrees
        :return: bool
        """

        if function in FUNC:
            command = ':SOUR{:d}:APPL:{} {:f},{:f},{:f},{:f}'.format(
                channel, FUNC[function], frequency, voltage, offset, phase
            )
            logger.debug('Setting waveform: "{}"'.format(command))
            self._write(command)
            return True
        else:
            logger.warn('Function "{}" not recognized!'.format(function))
            return False

    def on(self, ch=1):
        """ Turn channel on

        :param ch: int: channel
        :return: None
        """
        self._write('OUTP{:d} ON'.format(ch))
        return None


    def off(self, ch=1):
        """ Turn channel off

                :param ch: int: channel
                :return: None
                """
        logger.debug('Turn CH{} off'.format(ch))

        self._write('OUTP{:d} OFF'.format(ch))
        return None

    def close(self):
        """ Closes connection to device

        :return: None
        """
        logger.info('Closing instrument {}.'.format(self.instrID))
        self.off(1)
        self.off(2)
        self._initialized = False
        self._info = 'Unknown'
        self.instr.close()
        return None

    def __del__(self):
        self.close()


if __name__ == "__main__":
    import labtools.ids.ueye
    rig = Rigol()
    rig.init()

    print(rig._info)

    del rig
