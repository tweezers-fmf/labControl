"""
.. module:: flir.conf
   :synopsis: Configuration and constants

.. moduleauthor:: Ziga Gregorin <ziga.gregorin@ijs.si>

This is a configuration file. Paths and constants are specified here. For
tweaking and testing mainly... Should not be changed in principle...

"""
import PySpin

# Logging level, set to 'DEBUG' or 'INFO' to display messages in console. For debugging mainly...
LOGLEVEL = 'ERROR'


# initial camera constants
N_FRAMES = 100000
EXPOSURE = 30000.  # microseconds
EXPOSURE_AUTO = PySpin.ExposureAuto_Off  # {Off,Once,Continuous}
FRAME_RATE = 20.  # fps
PIXEL_FORMAT = PySpin.PixelFormat_Mono8  # {RGB8 for color}
ADC_BIT_DEPTH = PySpin.AdcBitDepth_Bit8
VIDEO_MODE = 7  # {0,1,7}
IMG_WIDTH = 1920
IMG_HEIGHT = 1200
X_OFFSET = 0
Y_OFFSET = 0
BLACK_LEVEL_CLAMPING = False
GAIN_AUTO = PySpin.GainAuto_Off  # {Off,Single,Continuous}
GAIN = 0.
GAMMA_ENABLE = False
TRIGGER_MODE = PySpin.TriggerMode_Off  # {On,Off}
TRIGGER_SOURCE = PySpin.TriggerSource_Software  # {Software,Line0}
ACQUISITION_MODE = PySpin.AcquisitionMode_Continuous  # {SingleFrame,MultiFrame,Continous}
IMAGE_FORMAT = 'PGM'
SERIAL = None

CALIBRATION = 1/0.3  # Mitutoyo 50x calibration