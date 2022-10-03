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

import PySpin
import time
import cv2
import numpy as np

from labtools.log import create_logger


locTime = time.localtime()
DAY = locTime.tm_mday
MONTH = locTime.tm_mon
YEAR = locTime.tm_year
HOUR = locTime.tm_hour
MINUTE = locTime.tm_min
dateToday = '_{0}-{1:02d}-{2:02d}-{3}-{4}_'.format(YEAR, MONTH, DAY, HOUR, MINUTE)

ENUM = 0

class config:
    N_FRAMES=100000
    EXPOSURE=30000. #microseconds
    EXPOSURE_AUTO = PySpin.ExposureAuto_Continuous  #{Off,Once,Continous}
    FRAME_RATE=20. #fps
    PIXEL_FORMAT=PySpin.PixelFormat_Mono8
    ADC_BIT_DEPTH=PySpin.AdcBitDepth_Bit8
    VIDEO_MODE=7 #{0,1,7}
    IMG_WIDTH=1920
    IMG_HEIGHT=300
    X_OFFSET=0
    Y_OFFSET=450
    BLACK_LEVEL_CLAMPING=False
    GAIN_AUTO=PySpin.GainAuto_Off #{Off,Single,Continuous}
    GAIN=0.
    GAMMA_ENABLE=False
    TRIGGER_MODE=PySpin.TriggerMode_Off #{On,Off}
    TRIGGER_SOURCE = PySpin.TriggerSource_Software #{Software,Line0}
    ACQUISITION_MODE = PySpin.AcquisitionMode_Continuous #{SingleFrame,MultiFrame,Continous}
    IMAGE_FORMAT = PySpin.PGM
    SERIAL = None


def print_device_info(cam):
    """
    This function prints the device information of the camera from the transport
    layer; please see NodeMapInfo example for more in-depth comments on printing
    device information from the nodemap.

    :param cam: Camera to get device information from.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """

    print('*** DEVICE INFORMATION ***\n')

    try:
        result = True
        nodemap = cam.GetTLDeviceNodeMap()

        node_device_information = PySpin.CCategoryPtr(nodemap.GetNode('DeviceInformation'))

        if PySpin.IsAvailable(node_device_information) and PySpin.IsReadable(node_device_information):
            features = node_device_information.GetFeatures()
            for feature in features:
                node_feature = PySpin.CValuePtr(feature)
                print('%s: %s' % (node_feature.GetName(),
                                  node_feature.ToString() if PySpin.IsReadable(node_feature) else 'Node not readable'))

        else:
            print('Device control information not available.')

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex.message)
        return False

    return result


def configure_custom_image_settings(cam):
    """
    Configures a number of settings on the camera including offsets X and Y,
    width, height, and pixel format. These settings must be applied before
    BeginAcquisition() is called; otherwise, those nodes would be read only.
    Also, it is important to note that settings are applied immediately.
    This means if you plan to reduce the width and move the x offset accordingly,
    you need to apply such changes in the appropriate order.

    :param cam: Camera to configure settings on.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    print('\n*** CONFIGURING CUSTOM IMAGE SETTINGS ***\n')

    try:
        result = True

        # Apply pixel format
        #
        # *** NOTES ***
        # In QuickSpin, enumeration nodes are as easy to set as other node
        # types. This is because enum values representing each entry node
        # are added to the API.
        if cam.PixelFormat.GetAccessMode() == PySpin.RW:
            cam.PixelFormat.SetValue(config.PIXEL_FORMAT)
            print('Pixel format set to %s...' % cam.PixelFormat.GetCurrentEntry().GetSymbolic())

        else:
            print('Pixel format not available...')
            result = False

        # Apply ADC Bit Depth
        if cam.AdcBitDepth.GetAccessMode() == PySpin.RW:
            cam.AdcBitDepth.SetValue(config.ADC_BIT_DEPTH)
            print("ADC Bit Depth set to %s." % cam.AdcBitDepth.GetCurrentEntry().GetSymbolic())
        else:
            print("ADC Bit Depth not available...")
            result = False

        # Set width
        #
        # *** NOTES ***
        # Other nodes, such as those corresponding to image width and height,
        # might have an increment other than 1. In these cases, it can be
        # important to check that the desired value is a multiple of the
        # increment.
        #
        # This is often the case for width and height nodes. However, because
        # these nodes are being set to their maximums, there is no real reason
        # to check against the increment.
        if cam.Width.GetAccessMode() == PySpin.RW and cam.Width.GetInc() != 0 and cam.Width.GetMax != 0:
            width_to_set = config.IMG_WIDTH
            width_to_set = min(cam.Width.GetMax(), width_to_set)
            cam.Width.SetValue(width_to_set)
            print('Width set to %i...' % cam.Width.GetValue())

        else:
            print('Width not available...')
            result = False

        # Set height
        #
        # *** NOTES ***
        # A maximum is retrieved with the method GetMax(). A node's minimum and
        # maximum should always be a multiple of its increment.
        if cam.Height.GetAccessMode() == PySpin.RW and cam.Height.GetInc() != 0 and cam.Height.GetMax != 0:
            height_to_set = config.IMG_HEIGHT
            height_to_set = min(cam.Height.GetMax(), height_to_set)
            cam.Height.SetValue(height_to_set)
            print('Height set to %i...' % cam.Height.GetValue())

        else:
            print('Height not available...')
            result = False

        # Apply offset X
        #
        # *** NOTES ***
        # Numeric nodes have both a minimum and maximum. A minimum is retrieved
        # with the method GetMin(). Sometimes it can be important to check
        # minimums to ensure that your desired value is within range.
        if cam.OffsetX.GetAccessMode() == PySpin.RW:
            xoff_to_set = config.X_OFFSET
            xoff_to_set = min(cam.OffsetX.GetMax(), xoff_to_set)
            xoff_to_set = max(cam.OffsetX.GetMin(), xoff_to_set)
            cam.OffsetX.SetValue(xoff_to_set)
            print('Offset X set to %d...' % cam.OffsetX.GetValue())

        else:
            print('Offset X not available...')
            result = False

        # Apply minimum to offset Y
        #
        # *** NOTES ***
        # It is often desirable to check the increment as well. The increment
        # is a number of which a desired value must be a multiple. Certain
        # nodes, such as those corresponding to offsets X and Y, have an
        # increment of 1, which basically means that any value within range
        # is appropriate. The increment is retrieved with the method GetInc().
        if cam.OffsetY.GetAccessMode() == PySpin.RW:
            yoff_to_set = config.Y_OFFSET
            yoff_to_set = min(cam.OffsetY.GetMax(), yoff_to_set)
            yoff_to_set = max(cam.OffsetY.GetMin(), yoff_to_set)
            cam.OffsetY.SetValue(yoff_to_set)
            print('Offset Y set to %d...' % cam.OffsetY.GetValue())

        else:
            print('Offset Y not available...')
            result = False

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False

    return result


def configure_framerate(cam):
    print("\n*** CONFIGURING FRAMERATE ***\n")
    try:
        result = True
        # if cam.AcquisitionFrameRateEnable.GetAccessMode() != PySpin.RW:
        #     print("Unable to enable manual frame rate. Aborting...")
        #     return False
        # cam.AcquisitionFrameRateEnable.SetValue(True)
        # print("Manual frame rate enabled.")
        if cam.AcquisitionFrameRate.GetAccessMode() != PySpin.RW:
            print("Unable to set frame rate. Aborting...")
            return False
        framerate_to_set = config.FRAME_RATE
        framerate_to_set = min(cam.AcquisitionFrameRate.GetMax(), framerate_to_set)
        cam.AcquisitionFrameRate.SetValue(framerate_to_set)
        print("Frame rate set to %d fps." % framerate_to_set)
    except PySpin.SpinnakerException as ex:
        print("Error: %s" % ex)
        result = False
    return result


def configure_blacklevel(cam):
    print("\n*** CONFIGURING BLACK LEVEL ***\n")
    try:
        result = True
        if cam.BlackLevelClampingEnable.GetAccessMode() != PySpin.RW:
            print("Unable to access Black Level Clamping settings. Aborting...")
            return False
        cam.BlackLevelClampingEnable.SetValue(config.BLACK_LEVEL_CLAMPING)
        print("Black level clamping set to %r." % config.BLACK_LEVEL_CLAMPING)
    except PySpin.SpinnakerException as ex:
        print("Error: %s" % ex)
        return False
    return result


def configure_gain(cam):
    print("\n*** CONFIGURING GAIN ***\n")
    try:
        result = True
        if cam.GainAuto.GetAccessMode() != PySpin.RW:
            print("Unable to access Auto Gain settings. Aborting...")
            return False
        cam.GainAuto.SetValue(config.GAIN_AUTO)
        print("Auto gain set to %s." % cam.GainAuto.GetCurrentEntry().GetSymbolic())
        if cam.Gain.GetAccessMode() != PySpin.RW:
            print("Unable to set gain. Aborting...")
            return False
        cam.Gain.SetValue(config.GAIN)
        print("Gain set to %f." % config.GAIN)
    except PySpin.SpinnakerException as ex:
        print("Error: %s" % ex)
        return False
    return result


def configure_gamma(cam):
    print("\n*** CONFIGURING GAMMA ***\n")
    try:
        result = True
        if cam.GammaEnable.GetAccessMode() != PySpin.RW:
            print("Unable to access Gamma settings. Aborting...")
            return False
        cam.GammaEnable.SetValue(config.GAMMA_ENABLE)
        print("Gamma Enable set to %r." % config.GAMMA_ENABLE)
    except PySpin.SpinnakerException as ex:
        print("Error: %s" % ex)
        return False
    return result


def configure_trigger(cam):
    print("\n*** CONFIGURING TRIGGER ***\n")
    try:
        result = True
        if cam.TriggerMode.GetAccessMode() != PySpin.RW:
            print("Unable to disable trigger mode (node retrieval). Aborting...")
            return False
        cam.TriggerMode.SetValue(PySpin.TriggerMode_Off)
        print("Trigger mode disabled.")
        if config.TRIGGER_MODE == PySpin.TriggerMode_On:
            if cam.TriggerSource.GetAccessMode() != PySpin.RW:
                print("Unable to get trigger source (node retrieval). Aborting...")
                return False
            if config.TRIGGER_SOURCE == PySpin.TriggerSource_Software:
                print("Software trigger chosen...")
            elif config.TRIGGER_SOURCE == PySpin.TriggerSource_Line0:
                print("Hardware trigger chosen...")
            cam.TriggerSource.SetValue(config.TRIGGER_SOURCE)
            cam.TriggerMode.SetValue(PySpin.TriggerMode_On)
            print("Trigger mode turned back on.")
    except PySpin.SpinnakerException as ex:
        print("Error: %s" % ex)
        return False
    return result


def configure_exposure(cam):
    """
     This function configures a custom exposure time. Automatic exposure is turned
     off in order to allow for the customization, and then the custom setting is
     applied.

     :param cam: Camera to configure exposure for.
     :type cam: CameraPtr
     :return: True if successful, False otherwise.
     :rtype: bool
    """

    print('\n*** CONFIGURING EXPOSURE ***\n')

    try:
        result = True

        # Turn off automatic exposure mode
        #
        # *** NOTES ***
        # Automatic exposure prevents the manual configuration of exposure
        # times and needs to be turned off for this example. Enumerations
        # representing entry nodes have been added to QuickSpin. This allows
        # for the much easier setting of enumeration nodes to new values.
        #
        # The naming convention of QuickSpin enums is the name of the
        # enumeration node followed by an underscore and the symbolic of
        # the entry node. Selecting "Off" on the "ExposureAuto" node is
        # thus named "ExposureAuto_Off".
        #
        # *** LATER ***
        # Exposure time can be set automatically or manually as needed. This
        # example turns automatic exposure off to set it manually and back
        # on to return the camera to its default state.

        if cam.ExposureAuto.GetAccessMode() != PySpin.RW:
            print('Unable to disable automatic exposure. Aborting...')
            return False

        cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
        print('Automatic exposure disabled...')

        # Set exposure time manually; exposure time recorded in microseconds
        #
        # *** NOTES ***
        # Notice that the node is checked for availability and writability
        # prior to the setting of the node. In QuickSpin, availability and
        # writability are ensured by checking the access mode.
        #
        # Further, it is ensured that the desired exposure time does not exceed
        # the maximum. Exposure time is counted in microseconds - this can be
        # found out either by retrieving the unit with the GetUnit() method or
        # by checking SpinView.

        if cam.ExposureTime.GetAccessMode() != PySpin.RW:
            print('Unable to set exposure time. Aborting...')
            return False

        # Ensure desired exposure time does not exceed the maximum
        exposure_time_to_set = config.EXPOSURE
        exposure_time_to_set = min(cam.ExposureTime.GetMax(), exposure_time_to_set)
        cam.ExposureTime.SetValue(exposure_time_to_set)
        print("Exposure time set to {:.2f} ms.".format(exposure_time_to_set/1000))

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    return result


def auto_exposure(cam):
    """
    This function returns the camera to a normal state by re-enabling automatic exposure.

    :param cam: Camera to reset exposure on.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    print('\n*** CONFIGURING AUTO EXPOSURE ***\n')

    try:
        result = True

        # Turn automatic exposure back on
        #
        # *** NOTES ***
        # Automatic exposure is turned on in order to return the camera to its
        # default state.

        if cam.ExposureAuto.GetAccessMode() != PySpin.RW:
            print('Unable to enable automatic exposure (node retrieval). Non-fatal error...')
            return False

        cam.ExposureAuto.SetValue(config.EXPOSURE_AUTO)
        symbolic = ['OFF', 'ONCE', 'CONTINOUS']
        print('Automatic exposure enabled set to %s' % symbolic[cam.ExposureAuto.GetValue()])

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    return result


def configure_chunk_data(nodemap):
    """
    This function configures the camera to add chunk data to each image. It does
    this by enabling each type of chunk data before enabling chunk data mode.
    When chunk data is turned on, the data is made available in both the nodemap
    and each image.

    :param nodemap: Transport layer device nodemap.
    :type nodemap: INodeMap
    :return: True if successful, False otherwise
    :rtype: bool
    """
    try:
        result = True
        print('\n*** CONFIGURING CHUNK DATA ***\n')

        # Activate chunk mode
        #
        # *** NOTES ***
        # Once enabled, chunk data will be available at the end of the payload
        # of every image captured until it is disabled. Chunk data can also be
        # retrieved from the nodemap.
        chunk_mode_active = PySpin.CBooleanPtr(nodemap.GetNode('ChunkModeActive'))

        if PySpin.IsAvailable(chunk_mode_active) and PySpin.IsWritable(chunk_mode_active):
            chunk_mode_active.SetValue(True)

        print('Chunk mode activated...')

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
            print('Unable to retrieve chunk selector. Aborting...\n')
            return False

        # Retrieve entries
        #
        # *** NOTES ***
        # PySpin handles mass entry retrieval in a different way than the C++
        # API. Instead of taking in a NodeList_t reference, GetEntries() takes
        # no parameters and gives us a list of INodes. Since we want these INodes
        # to be of type CEnumEntryPtr, we can use a list comprehension to
        # transform all of our collected INodes into CEnumEntryPtrs at once.
        entries = [PySpin.CEnumEntryPtr(chunk_selector_entry) for chunk_selector_entry in chunk_selector.GetEntries()]

        print('Enabling entries...')

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
                print('{} not available'.format(chunk_str))
                result = False
            elif chunk_enable.GetValue() is True:
                print('{} enabled'.format(chunk_str))
            elif PySpin.IsWritable(chunk_enable):
                chunk_enable.SetValue(True)
                print('{} enabled'.format(chunk_str))
            else:
                print('{} not writable'.format(chunk_str))
                result = False

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    return result


def configure_acquisition_mode(cam):
    """
     This function configures acquisitioin mode.

     :param cam: Camera to configure acquisition mode for.
     :type cam: CameraPtr
     :return: True if successful, False otherwise.
     :rtype: bool
    """
    print('\n*** IMAGE ACQUISITION ***\n')

    try:
        result = True

        # Set acquisition mode to continuous
        if cam.AcquisitionMode.GetAccessMode() != PySpin.RW:
            print('Unable to set acquisition mode to continuous. Aborting...')
            return False

        cam.AcquisitionMode.SetValue(config.ACQUISITION_MODE)
        print('Acquisition mode set to %s...' % cam.AcquisitionMode.GetCurrentEntry().GetSymbolic())

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    return result


def display_chunk_data_from_image(image, printQ=False, returnDict=False):
    """
    This function displays a select amount of chunk data from the image. Unlike
    accessing chunk data via the nodemap, there is no way to loop through all
    available data.

    :param returnDict: should it return dictionary with metadata?
    :param printQ: print out chunk data
    :param image: Image to acquire chunk data from
    :type image: Image object
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    if printQ:
        print('Printing chunk data from image...')
    cData = {}

    try:
        result = True
        if printQ:
            print(type(image))
        # Retrieve chunk data from image
        #
        # *** NOTES ***
        # When retrieving chunk data from an image, the data is stored in a
        # ChunkData object and accessed with getter functions.
        chunk_data = image.GetChunkData()

        # Retrieve frame ID
        frame_id = chunk_data.GetFrameID()
        if printQ:
            print('\tFrame ID: {}'.format(frame_id))
        cData['frame_id'] = frame_id

        # Retrieve width; width recorded in pixels
        width = chunk_data.GetWidth()
        if printQ:
            print('\tWidth: {}'.format(width))
        cData['width'] = width

        # Retrieve height; height recorded in pixels
        height = chunk_data.GetHeight()
        if printQ:
            print('\tHeight: {}'.format(height))
        cData['height'] = height

        # Retrieve offset X; offset X recorded in pixels
        offset_x = chunk_data.GetOffsetX()
        if printQ:
            print('\tOffset X: {}'.format(offset_x))
        cData['offset_x'] = offset_x

        # Retrieve offset Y; offset Y recorded in pixels
        offset_y = chunk_data.GetOffsetY()
        if printQ:
            print('\tOffset Y: {}'.format(offset_y))
        cData['offset_y'] = offset_y

        # Retrieve exposure time (recorded in microseconds)
        exposure_time = chunk_data.GetExposureTime()
        if printQ:
            print('\tExposure time: {} ns'.format(exposure_time))
        cData['exposure_time'] = exposure_time

        # Retrieve gain; gain recorded in decibels
        gain = chunk_data.GetGain()
        if printQ:
            print('\tGain: {}'.format(gain))
        cData['gain'] = gain

        # Retrieve sequencer set active
        sequencer_set_active = chunk_data.GetSequencerSetActive()
        if printQ:
            print('\tSequencer set active: {}'.format(sequencer_set_active))
        cData['sequencer_set_active'] = sequencer_set_active

        # Retrieve timestamp
        timestamp = chunk_data.GetTimestamp()
        if printQ:
            print('\tTimestamp: {}'.format(timestamp))
        cData['timestamp'] = timestamp

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    if returnDict:
        return cData
    return result


def configure_all(cam):
    result = True
    result &= configure_custom_image_settings(cam)
    result &= configure_gain(cam)
    result &= configure_gamma(cam)
    result &= configure_blacklevel(cam)
    result &= configure_exposure(cam)
    result &= configure_framerate(cam)
    result &= configure_trigger(cam)
    result &= configure_acquisition_mode(cam)
    result &= auto_exposure(cam)  # auto exposure
    result &= configure_chunk_data(cam.GetNodeMap())
    if cam.TLDevice.DeviceSerialNumber is not None and cam.TLDevice.DeviceSerialNumber.GetAccessMode() == PySpin.RO:
        config.SERIAL = cam.TLDevice.DeviceSerialNumber.GetValue()

    return result


def acquire_dummy_images(cam, num=1):
    """
    This function acquires and saves 'num' images from a device; please see
    Acquisition example for more in-depth comments on the acquisition of images.

    :param cam: Camera to acquire images from.
    :type cam: CameraPtr
    :param num: Number of acquired images.
    :type num: int
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    try:
        result = True
        # Begin acquiring images
        cam.BeginAcquisition()

        # Retrieve, convert, and save images
        for i in range(num):

            try:
                # Retrieve next received image and ensure image completion
                image_result = cam.GetNextImage()

                if image_result.IsIncomplete():
                    print('Image incomplete with image status %d...' % image_result.GetImageStatus())

                # Release image
                image_result.Release()

            except PySpin.SpinnakerException as ex:
                print('Error: %s' % ex)
                result = False

        # End acquisition
        cam.EndAcquisition()

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    return result


def acquire_image(cam, picName='BFLYpicture', savePic=True):
    """
    This function acquires and saves 1 image from a device; please see
    Acquisition example for more in-depth comments on the acquisition of images.

    :param savePic: save picture to disk?
    :param picName: filePath and filename for picture acquisition
    :param cam: Camera to acquire images from.
    :type cam: CameraPtr
    :return: ndarray, image metadata
    :rtype: ndarray, dict
    """
    global ENUM

    try:
        cam.BeginAcquisition()
        # Retrieve next received image and ensure image completion
        image_result = cam.GetNextImage()

        if image_result.IsIncomplete():
            print('Image incomplete with image status %d...' % image_result.GetImageStatus())
            img_array = None
            picData = False

        else:
            # Convert image
            image_converted = image_result.Convert(config.PIXEL_FORMAT, PySpin.HQ_LINEAR)

            # Save image
            if savePic:
                image_converted.Save(picName+dateToday+str(ENUM), config.IMAGE_FORMAT)
                ENUM += 1

            picData = display_chunk_data_from_image(image_result, returnDict=True)
            img_array = image_converted.GetNDArray()

        # Release image
        image_result.Release()
        cam.EndAcquisition()

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return None, False

    return img_array, picData

def acquire_images_for_flow(cam, num, picName='BFLYpicture', ROI=(0,0,1920,1200)):
    """
    This function acquires and saves 1 image from a device; please see
    Acquisition example for more in-depth comments on the acquisition of images.

    :param ROI: region of interest (x0, y0, x1, y1)
    :param num: number of saved pictures
    :param picName: filePath and filename for picture acquisition
    :param cam: Camera to acquire images from.
    :type cam: CameraPtr
    :return: ndarray, image metadata
    :rtype: ndarray, dict
    """
    global ENUM
    if cam.AcquisitionFrameRate.GetAccessMode() != PySpin.RW and cam.AcquisitionFrameRate.GetAccessMode() != PySpin.RO:
        print("Unable to get frame rate. Setting filename extention to config value...")
        fps = cam.AcquisitionFrameRate.GetValue()
    else:
        fps = config.FRAME_RATE
    picName += '_FPS%d' %fps

    x0, y0, x1, y1 = ROI

    avg_intensity = []

    cam.BeginAcquisition()

    for i in range(num):
        try:
            # Retrieve next received image and ensure image completion
            image_result = cam.GetNextImage()

            if image_result.IsIncomplete():
                print('Image incomplete with image status %d...' % image_result.GetImageStatus())

            else:
                # Convert image
                image_converted = image_result.Convert(config.PIXEL_FORMAT, PySpin.HQ_LINEAR)
                # Save image
                image_converted.Save(picName+dateToday+str(ENUM), config.IMAGE_FORMAT)
                ENUM += 1

                meta = display_chunk_data_from_image(image_result, returnDict=True)
                img = image_converted.GetNDArray()

                avg_intensity.append(np.mean(img[y0:y1, x0:x1])/meta['exposure_time'])

            # Release image
            image_result.Release()

        except PySpin.SpinnakerException as ex:
            print('Error: %s' % ex)
            return False

    cam.EndAcquisition()
    return np.array(avg_intensity)


def acquire_images(cam, num=10):
    """
    This function acquires num images from a device, stores them in a list, and returns the list.
    please see the Acquisition example for more in-depth comments on acquiring images.

    :param num: int: number of pictures
    :param cam: Camera to acquire images from.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: list(Image object)
    """
    try:
        result = True

        #  Begin acquiring images
        cam.BeginAcquisition()

        # Retrieve, convert, and save images
        images = list()

        for i in range(num):
            try:
                #  Retrieve next received image
                image_result = cam.GetNextImage()

                #  Ensure image completion
                if image_result.IsIncomplete():
                    print('Image incomplete with image status %d...' % image_result.GetImageStatus())

                else:
                    #  Convert image to mono 8 and append to list
                    images.append(image_result.Convert(config.PIXEL_FORMAT, PySpin.HQ_LINEAR))

                    #  Release image
                    image_result.Release()

            except PySpin.SpinnakerException as ex:
                print('Error: %s' % ex)
                result = False

        # End acquisition
        cam.EndAcquisition()

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    return images


def live_image(cam):
    """
    This function projects live image from a device
    :param cam: Camera to acquire images from.
    :type cam: CameraPtr
    :return: result
    :rtype: bool
    """

    try:
        result = True
        cam.BeginAcquisition()

        while True:
            image_result = cam.GetNextImage()
            image_converted = image_result.Convert(config.IMAGE_FORMAT, PySpin.HQ_LINEAR)
            img = image_converted.GetNDArray()
            cv2.imshow("LiveCam", img)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                image_result.Release()
                break

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    cam.EndAcquisition()
    return result

def live_image_ROI(cam, ROI):
    """
    This function projects live image from a device with rectangular ROI marker
    :param cam: Camera to acquire images from.
    :type cam: CameraPtr
    :param ROI: coordinates
    :return: result
    :rtype: bool
    """
    x0, y0, x1, y1 = ROI

    try:
        result = True
        cam.BeginAcquisition()

        while True:
            image_result = cam.GetNextImage()
            image_converted = image_result.Convert(config.IMAGE_FORMAT, PySpin.HQ_LINEAR)
            img = image_converted.GetNDArray()
            img = cv2.rectangle(img, (x0, y0), (x1, y1), 250, 3)
            cv2.imshow("LiveCam", img)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                image_result.Release()
                break

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    cam.EndAcquisition()
    return result


def print_genicam_device_info(cam):
    """
    Prints device information from the camera.

    *** NOTES ***
    Most camera interaction happens through GenICam nodes. The
    advantages of these nodes is that there is a lot more of them, they
    allow for a much deeper level of interaction with a camera, and no
    intermediate property (i.e. TLDevice or TLStream) is required. The
    disadvantage is that they require initialization.

    :param cam: Camera to get information from.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    try:
        result = True

        # Print exposure time
        if cam.ExposureTime.GetAccessMode() == PySpin.RO or cam.ExposureTime.GetAccessMode() == PySpin.RW:
            print('Exposure time: %s' % cam.ExposureTime.ToString())
        else:
            print('Exposure time: unavailable')
            result = False

        # Print black level
        if PySpin.IsReadable(cam.BlackLevel):
            print('Black level: %s' % cam.BlackLevel.ToString())
        else:
            print('Black level: unavailable')
            result = False

        # Print height
        if PySpin.IsReadable(cam.Height):
            print('Height: %s' % cam.Height.ToString())
        else:
            print('Height: unavailable')
            result = False

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False

    return result

def _main():
    result = True
    system=PySpin.System.GetInstance()
    cam_list = system.GetCameras()
    num_cameras = cam_list.GetSize()

    # Finish if there are no cameras
    if num_cameras == 0:
        # Clear camera list before releasing system
        cam_list.Clear()

        # Release system instance
        system.ReleaseInstance()

        print('Not enough cameras!')
        input('Done! Press Enter to exit...')
        return False

    cam = cam_list.GetByIndex(0)
    cam.Init()
    result &= configure_all(cam)


    try:
        # do work
        pass

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False
    finally:
        cam.DeInit()
        del cam
        cam_list.Clear()
        system.ReleaseInstance()
        input("Done! Press Enter to exit...")
        return result

if __name__ == '__main__':
    ID=0
    NUM_IMAGES=5
    _main()