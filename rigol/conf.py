"""
.. module:: rigol.conf
   :synopsis: Configuration and constants

.. moduleauthor:: Ziga Gregorin <ziga.gregorin@gmail.com>

This is a configuration file. Paths and constants are specified here. For
tweaking and testing mainly... Should not be changed in principle...

"""

INSTR = 'USB0::0x1AB1::0x0642::DG1ZA183802716::INSTR'
# Logging level, set to 'DEBUG' or 'INFO' to display messages in console. For debugging mainly...
LOGLEVEL = 'WARN'
FUNC = {
    'DC': 'DC',
    'sine': 'SIN',
    'square': 'SQU',
    'ramp': 'RAMP',
    'pulse': 'PULS',
    'noise': 'NOIS'
}