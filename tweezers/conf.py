# Logging level, set to 'DEBUG' or 'INFO' to display messages in console. For debugging mainly...
LOGLEVEL = 'INFO'

ERRORLIST = {
    '0':  "no error",
    '1':  "unknown command",
    '2':  "command active",
    '3':  "maximum number of force measurement traps exceeded",
    '4':  "manipulation traps not available under current license",
    '5':  "maximum number of manipulation traps exceeded",
    '6':  "trap out of working range",
    '7':  "invalid trap number",
    '8':  "invalid trap strength",
    '9':  "invalid trap position",
    '10': "maximum number of sequences exceeded",
    '11': "invalid sequence number",
    '12': "sequence assigned to trap - can't delete",
    '13': "invalid seq. rotation/camera parameter invalid",
    '14': "invalid seq. scale/camera parameter not set "
          "(no camera or invalid parameter)",
    '15': "invalid file name",
    '16': "invalid recording/snapshot type",
    '17': "error accessing video stream",
    '18': "recoding not possible",
    '19': "not possible to stop recording",
    '20': "invalid beam focus parameter",
    '21': "can not set beam focus",
    '22': "invalid laser level parameter",
    '23': "can not set laser level",
    '30': "TSF missing",
    '31': "TSF invalid data",
    '32': "TSF read/write error",
    '33': "TSF too long",
    '34': "TSF empty"
}