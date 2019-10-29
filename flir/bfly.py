"""
.. module: flir.bfly
    :synopsis FLIR/PointGrey BlackFly camera controller

.. moduleauthor:: Ziga Gregorin <ziga.gregorin@ijs.si>

Additional functions for Spinnaker SDK and easier access to BlackFly camera.


Spinnaker Full SDK has to be installed and working properly from
https://www.ptgrey.com/support/downloads

Developed and tested with Spinnaker for Python 2 and 3:
"spinnaker_python-1.19.0.22-cp36-cp36m-win_amd64"
    Spinnaker Full SDK 1.19.0.22
    Python 3.6
    Windows 10 x64

Additional libraries needed:
    time
    opencv-python
    numpy


"""
__author__ = 'Ziga Gregorin'

import numpy as np
import PySpin
import cv2
from labControl import flir as config

from labtools.log import create_logger
from labtools.utils.instr import InstrError, BaseDevice

import ArTwvStructure
import ctypes
import multiprocessing as mp

import timing
from os import listdir, makedirs

logger = create_logger(__name__, config.LOGLEVEL)


class Camera(object):
    """ Camera class for creation of a camera instance

        Creates a Bfly camera at a given index. At first camera initialization the camera list
        and number of cameras available is acquired.
    """
    __system = None
    __cam_list = None
    __num_cameras = None

    def __new__(cls, index=0):
        if cls.__system is None:
            cls.__system = PySpin.System.GetInstance()
            cls.__cam_list = cls.__system.GetCameras()
            cls.__num_cameras = cls.__cam_list.GetSize()

        logger.info('Starting bfly camera on index {}'.format(index))

        if index not in range(cls.__num_cameras):
            raise InstrError('Camera number {} too big. Total number {}'.format(index, cls.__num_cameras))
        return BflyCamera(cls.__cam_list.GetByIndex(index), index)


class BflyCamera(BaseDevice):
    """ BlackFly Camera controller for Spinnaker SDK

        Used for more user-friendly control of camera settings
        For accessing direct Spinnaker SDK commands for camera use self._camera

    """

    def __init__(self, CameraPtr, index=0):
        if not isinstance(CameraPtr, PySpin.CameraPtr):
            raise InstrError('Camera class is {} instead of PySpin.CameraPtr'.format(CameraPtr.__class__))
        self._device = index
        self._camera = CameraPtr
        self._info = self._getCameraName()

        self._imageFormat = PySpin.PGM  # default image format PGM = 0

        # filming
        self.__recording_video = False
        self.__recording_paused = False
        self.__video_file = None
        self._frames_recorded = 0
        self.__video_start_time = 0.0
        self.converted_image = None

    def init(self):
        """ Init camera """
        logger.info('Initializing camera')
        return self._camera.Init()

    @property
    def initialized(self):
        """ Boolean: is camera initialized """
        return self._camera.IsInitialized()

    def _getCameraName(self):
        """ Get Device model name for _info """
        nodemap = self._camera.GetTLDeviceNodeMap()
        node_device_information = PySpin.CCategoryPtr(nodemap.GetNode('DeviceInformation'))
        displayName = (node_device_information.GetFeatures()[5]).ToString()

        return displayName

    def printDeviceInfo(self):
        """
        This function prints the device information of the camera from the transport
        layer; please see NodeMapInfo example for more in-depth comments on printing
        device information from the nodemap.

        :return: True if successful, False otherwise.
        :rtype: bool
        """

        print('*** DEVICE INFORMATION ***\n')

        try:
            result = True
            nodemap = self._camera.GetTLDeviceNodeMap()

            node_device_information = PySpin.CCategoryPtr(nodemap.GetNode('DeviceInformation'))

            if PySpin.IsAvailable(node_device_information) and PySpin.IsReadable(node_device_information):
                features = node_device_information.GetFeatures()
                for feature in features:
                    node_feature = PySpin.CValuePtr(feature)
                    print('%s: %s' % (node_feature.GetName(),
                                      node_feature.ToString() if PySpin.IsReadable(
                                          node_feature) else 'Node not readable'))

            else:
                print('Device control information not available.')

        except PySpin.SpinnakerException as ex:
            print('Error: %s' % ex.message)
            return False

        return result

    # camera properties, reading and writing
    @property
    def exposure(self):
        """ Exposure time in microseconds """
        return self._camera.ExposureTime.GetValue()

    @exposure.setter
    def exposure(self, value):
        """ Exposure time in microseconds """

        if self.exposureAuto == 'Off' and self._camera.ExposureTime.GetAccessMode() == PySpin.RW:
            # Ensure desired exposure time does not exceed the maximum
            exposure_time_to_set = min(self._camera.ExposureTime.GetMax(), value)
            self._camera.ExposureTime.SetValue(exposure_time_to_set)
            logger.info('Exposure time set to {:.2f} ms.'.format(self.exposure / 1000))
        else:
            logger.warn('Can not set exposure time. ExposureAuto is set to "{}"'.format(self.exposureAuto))

    @property
    def exposureAuto(self):
        """ Automatic exposure """
        return self._camera.ExposureAuto.GetCurrentEntry().GetSymbolic()

    @exposureAuto.setter
    def exposureAuto(self, value):
        """ Set automatic exposure to 'Off', 'Once', 'Continous' """

        symbolic = {'Off': PySpin.ExposureAuto_Off,
                    'Once': PySpin.ExposureAuto_Once,
                    'Continuous': PySpin.ExposureAuto_Continuous}
        if self._camera.ExposureAuto.GetAccessMode() != PySpin.RW:
            logger.warn('Unable to change automatic exposure.')
        else:
            if value in symbolic:
                self._camera.ExposureAuto.SetValue(symbolic[value])
            else:
                self._camera.ExposureAuto.SetValue(value)
            logger.info('Auto exposure set to {}'.format(self.exposureAuto))

    @property
    def frameRate(self):
        """ Frame rate in FPS """
        return self._camera.AcquisitionFrameRate.GetValue()

    @frameRate.setter
    def frameRate(self, value):
        """ Frame rate in FPS """
        if self._camera.AcquisitionFrameRate.GetAccessMode() != PySpin.RW:
            logger.warn('Unable to set frame rate!')
        else:
            framerate_to_set = value
            framerate_to_set = min(self._camera.AcquisitionFrameRate.GetMax(), framerate_to_set)
            self._camera.AcquisitionFrameRate.SetValue(framerate_to_set)
            logger.info('Frame rate set to %d fps.' % self.frameRate)

    @property
    def pixelFormatSymbolic(self):
        """ Pixel format """
        return self._camera.PixelFormat.GetCurrentEntry().GetSymbolic()

    @property
    def pixelFormat(self):
        """ Pixel format """
        return self._camera.PixelFormat.GetValue()

    @pixelFormat.setter
    def pixelFormat(self, value):
        """ Pixel format """
        if self._camera.PixelFormat.GetAccessMode() == PySpin.RW:
            self._camera.PixelFormat.SetValue(value)
            logger.info('Pixel format set to {}'.format(self.pixelFormatSymbolic))
        else:
            logger.warn('Pixel format not available!')

    @property
    def adcBitDepth(self):
        """ ADC Bit Depth """
        return self._camera.AdcBitDepth.GetCurrentEntry().GetSymbolic()

    @adcBitDepth.setter
    def adcBitDepth(self, value):
        """ ADC Bit Depth """
        if self._camera.AdcBitDepth.GetAccessMode() == PySpin.RW:
            self._camera.AdcBitDepth.SetValue(value)
            logger.info('ADC Bit Depth set to %s.' % self.adcBitDepth)
        else:
            logger.warn('ADC Bit Depth not available...')

    @property
    def width(self):
        """ Picture width in pixels """
        return self._camera.Width.GetValue()

    @width.setter
    def width(self, value):
        """ Picture width in pixels """
        if self._camera.Width.GetAccessMode() == PySpin.RW and \
                self._camera.Width.GetInc() != 0 and self._camera.Width.GetMax != 0:
            width_to_set = min(self._camera.Width.GetMax(), value)
            self._camera.Width.SetValue(width_to_set)
            logger.info('Width set to %i...' % self.width)

        else:
            logger.warn('Width not available...')

    @property
    def height(self):
        """ Picture height in pixels """
        return self._camera.Height.GetValue()

    @height.setter
    def height(self, value):
        """ Picture height in pixels """
        if self._camera.Height.GetAccessMode() == PySpin.RW and \
                self._camera.Height.GetInc() != 0 and self._camera.Height.GetMax != 0:
            height_to_set = min(self._camera.Height.GetMax(), value)
            self._camera.Height.SetValue(height_to_set)
            logger.info('Height set to %i...' % self.height)

        else:
            logger.warn('Height not available...')

    @property
    def offsetX(self):
        """ x offset in pixels """
        return self._camera.OffsetX.GetValue()

    @offsetX.setter
    def offsetX(self, value):
        """ x offset in pixels """
        if self._camera.OffsetX.GetAccessMode() == PySpin.RW:
            xoff_to_set = min(self._camera.OffsetX.GetMax(), value)
            xoff_to_set = max(self._camera.OffsetX.GetMin(), xoff_to_set)
            self._camera.OffsetX.SetValue(xoff_to_set)
            logger.info('Offset X set to %d...' % self.offsetX)

        else:
            logger.warn('Offset X not available...')

    @property
    def offsetY(self):
        """ y offset in pixels """
        return self._camera.OffsetY.GetValue()

    @offsetY.setter
    def offsetY(self, value):
        """ y offset in pixels """
        if self._camera.OffsetY.GetAccessMode() == PySpin.RW:
            yoff_to_set = min(self._camera.OffsetY.GetMax(), value)
            yoff_to_set = max(self._camera.OffsetY.GetMin(), yoff_to_set)
            self._camera.OffsetY.SetValue(yoff_to_set)
            logger.info('Offset Y set to %d...' % self.offsetY)

        else:
            logger.warn('Offset Y not available...')

    @property
    def blackLevelClamping(self):
        """ Enable Black level clamping """
        return self._camera.BlackLevelClampingEnable.GetValue()

    @blackLevelClamping.setter
    def blackLevelClamping(self, value):
        """ Enable Black level clamping """
        if self._camera.BlackLevelClampingEnable.GetAccessMode() != PySpin.RW:
            logger.warn("Unable to access Black Level Clamping settings. Aborting...")
        else:
            self._camera.BlackLevelClampingEnable.SetValue(value)
            logger.info("Black level clamping set to %r." % self.blackLevelClamping)

    @property
    def gainAuto(self):
        """ Automatic gain """
        return self._camera.GainAuto.GetCurrentEntry().GetSymbolic()

    @gainAuto.setter
    def gainAuto(self, value):
        """ Set automatic gain to 'Off', 'Once', 'Continous' """

        symbolic = {'Off': PySpin.GainAuto_Off,
                    'Once': PySpin.GainAuto_Once,
                    'Continous': PySpin.GainAuto_Continuous}
        if self._camera.GainAuto.GetAccessMode() != PySpin.RW:
            logger.warn('Unable to change automatic gain.')
        else:
            if value in symbolic:
                self._camera.GainAuto.SetValue(symbolic[value])
            else:
                self._camera.GainAuto.SetValue(value)
            logger.info('Auto gain set to {}'.format(self.gainAuto))

    @property
    def gain(self):
        """ Gain """
        return self._camera.Gain.GetValue()

    @gain.setter
    def gain(self, value):
        """ Set gain value if it is not automatic """

        if self.gainAuto == 'Off' and self._camera.Gain.GetAccessMode() == PySpin.RW:
            self._camera.Gain.SetValue(value)
            logger.info('Gain set to {}'.format(self.gain))
        else:
            logger.warn('Can not set gain. Auto gain set to "{}"'.format(self.gainAuto))

    @property
    def gammaEnable(self):
        """ Gamma enable """
        return self._camera.GammaEnable.GetValue()

    @gammaEnable.setter
    def gammaEnable(self, value):
        """ Set gamma enable """

        if self._camera.GammaEnable.GetAccessMode() != PySpin.RW:
            logger.warn("Unable to access Gamma settings. Aborting...")
        else:
            self._camera.GammaEnable.SetValue(value)
            logger.info("Gamma Enable set to %r." % self.gammaEnable)

    @property
    def triggerMode(self):
        """ Trigger mode """
        return self._camera.TriggerMode.GetCurrentEntry().GetSymbolic()

    @triggerMode.setter
    def triggerMode(self, value):
        """ Set trigger mode on/off"""
        if self._camera.TriggerMode.GetAccessMode() != PySpin.RW:
            logger.warn("Unable to set trigger mode.")
        else:
            self._camera.TriggerMode.SetValue(value)
            logger.info("Trigger mode disabled.")

    @property
    def triggerSource(self):
        """ Trigger source """
        return self._camera.TriggerSource.GetCurrentEntry().GetSymbolic()

    @triggerSource.setter
    def triggerSource(self, value):
        """ Trigger source could be Software or Line0"""
        if self.triggerMode == PySpin.TriggerMode_On:
            # turn trigger mode off
            self.triggerMode = PySpin.TriggerMode_Off

            if self._camera.TriggerSource.GetAccessMode() != PySpin.RW:
                logger.warn("Unable to get trigger source (node retrieval). Aborting...")
            else:
                self._camera.TriggerSource.SetValue(value)
                logger.info('Trigger sest to {}'.format(self.triggerSource))

            # set trigger mode on
            self.triggermode = PySpin.TriggerMode_On
        else:
            logger.warn('Can not set Trigger source while Trigger mode is Off')

    @property
    def acquisitionMode(self):
        """ Acquisition mode"""
        return self._camera.AcquisitionMode.GetCurrentEntry().GetSymbolic()

    @acquisitionMode.setter
    def acquisitionMode(self, value):
        """ Acquisition mode set to SingleFrame, MultiFrame, Continous """

        symbolic = {'SingleFrame': PySpin.AcquisitionMode_SingleFrame,
                    'MultiFrame': PySpin.AcquisitionMode_MultiFrame,
                    'Continous': PySpin.AcquisitionMode_Continuous}

        if self._camera.AcquisitionMode.GetAccessMode() != PySpin.RW:
            logger.warn('Unable to change acquisition mode.')
        else:
            if value in symbolic:
                self._camera.AcquisitionMode.SetValue(symbolic[value])
            else:
                self._camera.AcquisitionMode.SetValue(value)
            logger.info('Acquisition mode set to {}'.format(self.acquisitionMode))

    @property
    def imageFormatSymbolic(self):
        """ Image saving format """
        symbolic = {0: 'PGM',
                    1: 'PPM',
                    2: 'BMP',
                    3: 'JPEG',
                    4: 'JPEG2000',
                    5: 'TIFF',
                    6: 'PNG',
                    7: 'RAW'}
        return symbolic[self._imageFormat]

    @property
    def imageFormat(self):
        """ Image saving format """
        return self._imageFormat

    @imageFormat.setter
    def imageFormat(self, value):
        """ Set image format: PGM, PPM, BMP, JPEG, TIFF, PNG, RAW """
        symbolic = {'PGM': PySpin.PGM,
                    'PPM': PySpin.PPM,
                    'BMP': PySpin.BMP,
                    'JPEG': PySpin.JPEG,
                    'JPEG2000': PySpin.JPEG2000,
                    'TIFF': PySpin.TIFF,
                    'PNG': PySpin.PNG,
                    'RAW': PySpin.RAW}

        if value in symbolic:
            self._imageFormat = symbolic[value]
            logger.info('Image format set to {}'.format(self.imageFormatSymbolic))
        else:
            logger.warn('Image format "{}" not found!'.format(value))

    def configureAll(self):
        """ Configure camera properties with values from config file """
        self.exposureAuto = config.EXPOSURE_AUTO
        self.exposure = config.EXPOSURE
        self.frameRate = config.FRAME_RATE
        self.pixelFormat = config.PIXEL_FORMAT
        self.adcBitDepth = config.ADC_BIT_DEPTH
        self.width = config.IMG_WIDTH
        self.height = config.IMG_HEIGHT
        self.offsetX = config.X_OFFSET
        self.offsetY = config.Y_OFFSET
        self.blackLevelClamping = config.BLACK_LEVEL_CLAMPING
        self.gainAuto = config.GAIN_AUTO
        self.gain = config.GAIN
        self.gammaEnable = config.GAMMA_ENABLE
        self.triggerMode = config.TRIGGER_MODE
        self.triggerSource = config.TRIGGER_SOURCE
        self.acquisitionMode = config.ACQUISITION_MODE
        self.imageFormat = config.IMAGE_FORMAT
        self.configureChunkData()

    def configureChunkData(self):
        """
        This function configures the camera to add chunk data to each image. It does
        this by enabling each type of chunk data before enabling chunk data mode.
        When chunk data is turned on, the data is made available in both the nodemap
        and each image.

        :return: True if successful, False otherwise
        :rtype: bool
        """
        try:
            result = True
            logger.info('*** CONFIGURING CHUNK DATA ***')

            # Activate chunk mode
            #
            # *** NOTES ***
            # Once enabled, chunk data will be available at the end of the payload
            # of every image captured until it is disabled. Chunk data can also be
            # retrieved from the nodemap.
            nodemap = self._camera.GetNodeMap()
            chunk_mode_active = PySpin.CBooleanPtr(nodemap.GetNode('ChunkModeActive'))

            if PySpin.IsAvailable(chunk_mode_active) and PySpin.IsWritable(chunk_mode_active):
                chunk_mode_active.SetValue(True)

            logger.info('Chunk mode activated...')

            # Enable all types of chunk data
            #
            # *** NOTES ***
            # Enabling chunk data requires working with nodes: "ChunkSelector"
            # is an enumeration selector node and "ChunkEnable" is a boolean. It
            # requires retrieving the selector node (which is of enumeration node
            # type), selecting the entry of the chunk data to be enabled, retrieving
            # the corresponding boolean, and setting it to be true.
            #
            # In this example, all chunk data is enabled, so these steps are
            # performed in a loop. Once this is complete, chunk mode still needs to
            # be activated.
            chunk_selector = PySpin.CEnumerationPtr(nodemap.GetNode('ChunkSelector'))

            if not PySpin.IsAvailable(chunk_selector) or not PySpin.IsReadable(chunk_selector):
                logger.warn('Unable to retrieve chunk selector. Aborting...\n')
                return False

            # Retrieve entries
            #
            # *** NOTES ***
            # PySpin handles mass entry retrieval in a different way than the C++
            # API. Instead of taking in a NodeList_t reference, GetEntries() takes
            # no parameters and gives us a list of INodes. Since we want these INodes
            # to be of type CEnumEntryPtr, we can use a list comprehension to
            # transform all of our collected INodes into CEnumEntryPtrs at once.
            entries = [PySpin.CEnumEntryPtr(chunk_selector_entry) for chunk_selector_entry in
                       chunk_selector.GetEntries()]

            logger.info('Enabling entries...')

            # Iterate through our list and select each entry node to enable
            for chunk_selector_entry in entries:
                # Go to next node if problem occurs
                if not PySpin.IsAvailable(chunk_selector_entry) or not PySpin.IsReadable(chunk_selector_entry):
                    continue

                chunk_selector.SetIntValue(chunk_selector_entry.GetValue())

                chunk_str = '\t {}:'.format(chunk_selector_entry.GetSymbolic())

                # Retrieve corresponding boolean
                chunk_enable = PySpin.CBooleanPtr(nodemap.GetNode('ChunkEnable'))

                # Enable the boolean, thus enabling the corresponding chunk data
                if not PySpin.IsAvailable(chunk_enable):
                    logger.warn('{} not available'.format(chunk_str))
                    result = False
                elif chunk_enable.GetValue() is True:
                    logger.info('{} enabled'.format(chunk_str))
                elif PySpin.IsWritable(chunk_enable):
                    chunk_enable.SetValue(True)
                    logger.info('{} enabled'.format(chunk_str))
                else:
                    logger.warn('{} not writable'.format(chunk_str))
                    result = False

        except PySpin.SpinnakerException as ex:
            print('Error: %s' % ex)
            result = False

        return result

    # functions for acquiring images and saving them
    def BeginAcquisition(self):
        """ begins acquisition """
        return self._camera.BeginAcquisition()

    def EndAcquisition(self):
        """ end acquisition """
        return self._camera.EndAcquisition()

    @property
    def isStreaming(self):
        """ Boolean: is camera streaming """
        return self._camera.IsStreaming()

    @property
    def isRecording(self):
        """ Boolean: is recording active """
        return self.__recording_video

    def GetNextImage(self, *args):
        """ Get next image from buffer and return image

            Use this for directly acquiring images from camera for faster acquisition
        """
        return self._camera.GetNextImage(*args)

    def getNextImageArray(self):
        """ Collect next image and convert it to Image class

            Converts image to BflyImage class with numpy array and additional data
        """
        image_result = self.GetNextImage()
        image_converted = image_result.Convert(self.pixelFormat, PySpin.HQ_LINEAR)

        img = image_converted.GetNDArray()
        meta = getMetaData(image_result)

        # release image from buffer
        image_result.Release()

        return BflyImage(img, meta)

    def liveImage(self):
        """ This function projects live image from a device
            Press 'q' to close the video stream
        """
        print('Press "q" to close.')

        try:
            result = True
            self.BeginAcquisition()

            while True:
                image_result = self.GetNextImage()
                image_converted = image_result.Convert(self.pixelFormat, PySpin.HQ_LINEAR)
                img = image_converted.GetNDArray()
                cv2.imshow("LiveCam", img)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    cv2.destroyAllWindows()
                    image_result.Release()
                    break

        except PySpin.SpinnakerException as ex:
            result = False
            print('Error: %s' % ex)
        self.EndAcquisition()
        return result

    def acquireImages(self, num=1, name='BflyTestImage'):
        """ Acquire images and save them to disk

        :param num: number of pictures
        :param name: file path and name
        :return:
        """
        logger.debug('Acquire {} images with name {}'.format(num, name))

        self.BeginAcquisition()

        for i in range(num):
            try:
                #  Retrieve next received image
                image_result = self.GetNextImage()

                #  Ensure image completion
                if image_result.IsIncomplete():
                    print('Image incomplete with image status %d...' % image_result.GetImageStatus())

                else:
                    #  Save image to disk
                    image_result.Save(name + timing.dateToday() + '{:05d}'.format(i), self.imageFormat)

                    #  Release image
                    image_result.Release()

            except PySpin.SpinnakerException as ex:
                print('Error: %s' % ex)

        self.EndAcquisition()

    # TWV movie recording
    def start_recording(self, file_name):
        """Starts video recording to twv file"""

        if not self.__recording_video:

            # check if the file extension is proper, otherwise add .twv
            if not file_name.endswith('.twv'):
                file_name += '.twv'

            file_name = file_name.replace('\\', '/')  # path has only / separator

            # check if the folder exist, create if it does not
            path = '/'.join(file_name.split('/')[:-1])
            if path:
                makedirs(path, exist_ok=True)

            # check that the file does not exist already, prevent overwriting - add '1' to file name
            if file_name.split('/')[-1] in listdir(path):
                tempName = file_name.split('.')
                tempName[-2] += '1'
                file_name = '.'.join(tempName)

            # open file for writing video data in binary
            logger.debug("Writing to " + file_name)
            self.__video_file = open(file_name, "wb")
            video_header = ArTwvStructure.TArVideoHeader()

            if not self.isStreaming:
                # start streaming
                self.BeginAcquisition()

            if not self.converted_image:
                # if there is no current image, capture one
                self.capture()

            self.__video_file.write(video_header)
            self._frames_recorded = 0
            self.__recording_video = True
            self.__video_start_time = self.converted_image.GetTimeStamp()
            return 0

    def stop_recording(self):
        """Stops undergoing video recording"""
        if self.__recording_video:
            # move to the beginning of the file
            self.__video_file.seek(0)

            # get file header pointers and set attributes of the header
            video_header = ArTwvStructure.TArVideoHeader()
            calibration_data = ArTwvStructure.TArCalibrationData()
            setattr(calibration_data, 'ImageToSampleScale', config.CALIBRATION)

            setattr(video_header, "VideoID", 0x1A57)
            setattr(video_header, "VideoVersion", 20)
            setattr(video_header, "RecordedFrames", self._frames_recorded)
            setattr(video_header, "VideoHeaderSize", ctypes.sizeof(video_header))
            setattr(video_header, "CalibrationData", calibration_data)

            frame_data = ArTwvStructure.TArFrameData()
            frame_roi = ArTwvStructure.TArFrameROI()
            setattr(frame_roi, "Width", self.width)
            setattr(frame_roi, "Height", self.height)
            setattr(frame_roi, "Top", self.offsetY)
            setattr(frame_roi, "Left", self.offsetX)

            setattr(frame_data, "HeaderSize", ctypes.sizeof(ArTwvStructure.TArFrameHeader()))
            setattr(frame_data, "ROI", frame_roi)
            setattr(frame_data, "BytesPerPixel", 1)
            setattr(frame_data, "FrameRate", self.frameRate)
            setattr(frame_data, "Exposure", self.exposure / 1000.0)
            setattr(frame_data, "Gain", self.gain)
            setattr(video_header, "FrameData", frame_data)

            # write header data and close file
            self.__video_file.write(video_header)
            self.__video_file.close()
            logger.debug("Written " + str(self._frames_recorded) + " frames.")
            self.__recording_video = False
            self.__video_file = None
        return 0

    def add_frame_to_video(self):
        frame_header = ArTwvStructure.TArFrameHeader()
        setattr(frame_header, "FrameNumber", self._frames_recorded)
        setattr(frame_header, "FrameTime", (self.converted_image.GetTimeStamp() - self.__video_start_time) * 1e-9)
        self.__video_file.write(frame_header)
        self.__video_file.write(self.converted_image.GetData().tobytes())
        self._frames_recorded += 1

        return None

    def fileClosed(self):
        """ Check if the video file is closed

        :return: bool: file closed status
        """
        if self.__video_file is None:
            return True
        return self.__video_file.closed

    def capture(self):
        """ Get the next frame in queue and store it in the camera class as current frame
            If recording is active, add the frame to TWV file.

        :return: None
        """
        img = self.GetNextImage()
        self.converted_image = img.Convert(self.pixelFormat, PySpin.HQ_LINEAR)
        img.Release()

        # add the new acquired frame to the video if recording is on
        if self.__recording_video:
            self.add_frame_to_video()

    def close(self):
        """ Close the device """
        logger.info('Closing device')
        # close stream
        if self.isStreaming:
            self.EndAcquisition()

        # delete info
        self._info = 'Unknown'
        self._camera.DeInit()

    def __del__(self):
        self.close()


class BflyImage:
    def __init__(self, image, meta):
        """ Black fly image with properties

            Has stored image value in numpy array and metadata,
            that are added directly to class __dict__
        """
        self.image = image
        self.__dict__.update(meta)


class CameraProcess(mp.Process):
    """ Black Fly camera process for creating a camera instance in a separate process

    """
    def __init__(self, stopEvent: mp.Event, recEvent: mp.Event, recStopEvent: mp.Event,
                 recName, cameraIndex=0):
        mp.Process.__init__(self)
        self.stopped = stopEvent  # event for stopping the process
        self.recStart = recEvent  # event for starting the recording
        self.recStop = recStopEvent  # event for stopping the recording
        self.recName = recName  # dictionary with file name at ['fname']
        self.name = 'Cam_{:d}'.format(cameraIndex)
        self.cInd = cameraIndex

    def run(self):
        logger.info('Starting camera process')
        c = Camera(self.cInd)

        # init camera
        if not c.initialized:
            logger.info('Process: Initializing camera')
            c.init()
            c.configureAll()
            c.frameRate = 10  # slow frame rate for testing
        logger.info('Frame rate on {}: {} FPS'.format(self.name, c.frameRate))

        # start stream
        c.BeginAcquisition()
        # checkTime = timing.now()
        try:
            while not self.stopped.is_set():
                c.capture()

                if self.recStop.is_set():
                    logger.debug('Cam: Stop recording')
                    c.stop_recording()

                if self.recStart.is_set():
                    fname = self.recName['fname']
                    print('\nfile name = ' + fname)

                    logger.debug('Cam: Start recording file {}'.format(fname))
                    c.start_recording(fname)
                    self.recStart.clear()

                # # live video - not working yet
                # if timing.now() - checkTime > 0.2:  # if enough time passed, show picture
                #     # print('Cam: draw picture')
                #     cv2.imshow('LiveVideo', c.converted_image.GetNDArray())
                #     if cv2.waitKey(1) & 0xFF == ord('q'):
                #         break
                #     checkTime = timing.now()

        except Exception as e:
            print(e)

        finally:
            logger.debug('Cam: exit strategy')
            cv2.destroyAllWindows()

            del c


def getMetaData(image):
    """
    This function displays a select amount of chunk data from the image. Unlike
    accessing chunk data via the nodemap, there is no way to loop through all
    available data.

    :param image: Image to acquire chunk data from
    :type image: Image object
    :return: picure meta data
    :rtype: dict
    """

    cData = {}

    try:
        # Retrieve chunk data from image
        #
        # *** NOTES ***
        # When retrieving chunk data from an image, the data is stored in a
        # ChunkData object and accessed with getter functions.
        chunk_data = image.GetChunkData()

        # Retrieve frame ID
        frame_id = chunk_data.GetFrameID()
        cData['frame_id'] = frame_id

        # Retrieve width; width recorded in pixels
        width = chunk_data.GetWidth()
        cData['width'] = width

        # Retrieve height; height recorded in pixels
        height = chunk_data.GetHeight()
        cData['height'] = height

        # Retrieve offset X; offset X recorded in pixels
        offset_x = chunk_data.GetOffsetX()
        cData['offset_x'] = offset_x

        # Retrieve offset Y; offset Y recorded in pixels
        offset_y = chunk_data.GetOffsetY()
        cData['offset_y'] = offset_y

        # Retrieve exposure time (recorded in microseconds)
        exposure_time = chunk_data.GetExposureTime()
        cData['exposure_time'] = exposure_time

        # Retrieve gain; gain recorded in decibels
        gain = chunk_data.GetGain()
        cData['gain'] = gain

        # Retrieve sequencer set active
        sequencer_set_active = chunk_data.GetSequencerSetActive()
        cData['sequencer_set_active'] = sequencer_set_active

        # Retrieve timestamp
        timestamp = chunk_data.GetTimestamp()
        cData['timestamp'] = timestamp

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)

    return cData


def liveStreamProcess(imageArray: mp.Array, delayTime=0.2):
    """ Function for displaying live image

    :param imageArray:
    :param delayTime:
    :return:
    """
    # TODO: write a function for live streaming current images from a source
    while True:
        image = np.array(imageArray.value)
        timing.sleep(delayTime)


if __name__ == '__main__':

    manager = mp.Manager()
    recStart = mp.Event()  # start recording
    recStop = mp.Event()  # stop recording
    stopper = mp.Event()  # stop stream
    fileName = manager.dict()


    tempImage = mp.Array('i', 1920*1200)

    cProc = CameraProcess(stopper, recStart, recStop, fileName, 0)
    cProc.start()

    timing.sleep(2)

    # fileName.value = b'C:\\Users\\IJS-Gregorin\\Documents\\meritveDisk\\test\\TestVideo2.twv'
    fileName['fname'] = '../test/DefaultVideo.twv'
    while True:
        inp = input('What would you do? ')
        if inp == 'start':
            recStart.set()
        elif inp == 'stop':
            recStop.set()
        elif inp == 'kill':
            stopper.set()
            break
        else:
            print('Command not recognized')

    # timing.sleep(1)
    # print('Start recording')
    # recStart.set()
    # timing.sleep(3)
    # print('Stop recording')
    # recStop.set()
    # timing.sleep(1)
    # print('Stop program')
    # stopper.set()

    cProc.join()
    print('Finished')
