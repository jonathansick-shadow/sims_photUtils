import numpy

__all__ = ["PhotometricParameters"]

class DefaultPhotometricParameters:
    """
    This class will just contain a bunch of dict which store
    the default PhotometricParameters for LSST Bandpasses

    Users should not access this class (which is why it is
    not included in the __all__ declaration for this file).

    It is only used to initialize PhotometricParameters off of
    a bandpass name.
    """

    # Obviously, some of these parameters (effarea, gain, platescale,
    # darkcurrent, and readnoise) will not change as a function of bandpass;
    # we are just making them dicts here to be consistent with
    # everything else (and to make it possible for
    # PhotometricParameters to access them using the bandpass name
    # passed to its constructor)
    #
    # Note: all dicts contain an 'any' key which will be the default
    # value if an unknown bandpass is asked for
    #
    # 'any' values should be kept consistent with r band

    bandpassNames = ['u', 'g', 'r', 'i', 'z', 'y', 'any']

    # exposure time in seconds
    exptime = {'u':15.0, 'g':15.0, 'r':15.0, 'i':15.0, 'z':15.0, 'y':15.0,
               'any':15.0}

    # number of exposures
    nexp = {'u':2, 'g':2, 'r':2, 'i':2, 'z':2, 'y':2,
            'any':2}

    # effective area in cm^2
    effarea = {'u': 3.31830724e5,
               'g': 3.31830724e5,
               'r': 3.31830724e5,
               'i': 3.31830724e5,
               'z': 3.31830724e5,
               'y': 3.31830724e5,
               'any': 3.31830724e5}

    # electrons per ADU
    gain = {'u':2.3, 'g':2.3, 'r':2.3, 'i':2.3, 'z':2.3, 'y':2.3,
            'any':2.3}

    # electrons per pixel per exposure
    readnoise = {'u':5.0, 'g':5.0, 'r':5.0, 'i':5.0, 'z':5.0, 'y':5.0,
                 'any':5.0}

    # electrons per pixel per second
    darkcurrent = {'u':0.2, 'g':0.2, 'r':0.2, 'i':0.2, 'z':0.2, 'y':0.2,
                   'any':0.2}

    # electrons per pixel per exposure
    othernoise = {'u':4.69, 'g':4.69, 'r':4.69, 'i':4.69, 'z':4.69, 'y':4.69,
                  'any':4.69}

    # arcseconds per pixel
    platescale = {'u':0.2, 'g':0.2, 'r':0.2, 'i':0.2, 'z':0.2, 'y':0.2,
                  'any':0.2}

    # systematic squared error in magnitudes
    # see Table 14 of the SRD document
    # https://docushare.lsstcorp.org/docushare/dsweb/Get/LPM-17
    sigmaSys = {'u':0.0075, 'g':0.005, 'r':0.005, 'i':0.005, 'z':0.0075, 'y':0.0075,
                'any':0.005}


class PhotometricParameters(object):

    def __init__(self, exptime=None,
                 nexp=None,
                 effarea=None,
                 gain=None,
                 readnoise=None,
                 darkcurrent=None,
                 othernoise=None,
                 platescale=None,
                 sigmaSys=None,
                 bandpass=None):

        """
        @param [in] exptime exposure time in seconds (defaults to LSST value)

        @param [in] nexp number of exposures (defaults to LSST value)

        @param [in] effarea effective area in cm^2 (defaults to LSST value)

        @param [in] gain electrons per ADU (defaults to LSST value)

        @param [in] readnoise electrons per pixel per exposure (defaults to LSST value)

        @param [in] darkcurrent electons per pixel per second (defaults to LSST value)

        @param [in] othernoise electrons per pixel per exposure (defaults to LSST value)

        @param [in] platescale arcseconds per pixel (defaults to LSST value)

        @param [in] sigmaSys systematic error in magnitudes
        (defaults to LSST value)

        @param [in] bandpass is the name of the bandpass to which these parameters
        correspond.  If set to an LSST bandpass, the constructor will initialize
        PhotometricParameters to LSST default values for that bandpass, excepting
        any parameters that have been set by hand, i.e

        myPhotParams = PhotometricParameters(nexp=3, bandpass='u')

        will initialize a PhotometricParameters object to u bandpass defaults, except
        with 3 exposures instead of 2.

        If bandpass is left as None, other parameters will default to LSST r band
        values (except for those values set by hand).  The bandpass member variable
        of PhotometricParameters will, however, remain None.
        """

        # readnoise, darkcurrent and othernoise are measured in electrons.
        # This is taken from the specifications document LSE-30 on Docushare
        # Section 3.4.2.3 states that the total noise per pixel shall be 12.7 electrons
        # which the defaults sum to (remember to multply darkcurrent by the number
        # of seconds in an exposure=15).

        self._exptime = None
        self._nexp = None
        self._effarea = None
        self._gain = None
        self._platescale = None
        self._sigmaSys = None
        self._readnoise = None
        self._darkcurrent = None
        self._othernoise = None

        self._bandpass = bandpass
        defaults = DefaultPhotometricParameters()

        if bandpass is None:
            bandpassKey = 'any'
            # This is so we do not set the self._bandpass member variable
            # without the user's explicit consent, but we can still access
            # default values from the PhotometricParameterDefaults
        else:
            bandpassKey = bandpass

        if bandpassKey in defaults.bandpassNames:
            self._exptime = defaults.exptime[bandpassKey]
            self._nexp = defaults.nexp[bandpassKey]
            self._effarea = defaults.effarea[bandpassKey]
            self._gain = defaults.gain[bandpassKey]
            self._platescale = defaults.platescale[bandpassKey]
            self._sigmaSys = defaults.sigmaSys[bandpassKey]
            self._readnoise = defaults.readnoise[bandpassKey]
            self._darkcurrent = defaults.darkcurrent[bandpassKey]
            self._othernoise = defaults.othernoise[bandpassKey]

        if exptime is not None:
            self._exptime = exptime

        if nexp is not None:
            self._nexp = nexp

        if effarea is not None:
            self._effarea = effarea

        if gain is not None:
            self._gain = gain

        if platescale is not None:
            self._platescale = platescale

        if sigmaSys is not None:
            self._sigmaSys = sigmaSys

        if readnoise is not None:
            self._readnoise = readnoise

        if darkcurrent is not None:
            self._darkcurrent = darkcurrent

        if othernoise is not None:
            self._othernoise = othernoise

        failureMessage = ''
        failureCt = 0

        if self._exptime is None:
            failureMessage += 'did not set exptime\n'
            failureCt += 1

        if self._nexp is None:
            failureMessage += 'did not set nexp\n'
            failureCt += 1

        if self._effarea is None:
            failureMessage += 'did not set effarea\n'
            failureCt += 1

        if self._gain is None:
            failureMessage += 'did not set gain\n'
            failureCt += 1

        if self._platescale is None:
            failureMessage += 'did not set platescale\n'
            failureCt +=1

        if self._sigmaSys is None:
            failureMessage += 'did not set sigmaSys\n'
            failureCt += 1

        if self._readnoise is None:
            failureMessage += 'did not set readnoise\n'
            failureCt += 1

        if self._darkcurrent is None:
            failureMessage += 'did not set darkcurrent\n'
            failureCt +=1

        if self._othernoise is None:
            failureMessage += 'did not set othernoise\n'
            failureCt += 1

        if failureCt>0:
            raise RuntimeError('In PhotometricParameters:\n%s' % failureMessage)



    @property
    def bandpass(self):
        """
        The name of the bandpass associated with these parameters (can be None)
        """
        return self._bandpass

    @bandpass.setter
    def bandpass(self, value):
        raise RuntimeError("You should not be setting bandpass on the fly; " +
                           "Just instantiate a new case of PhotometricParameters")

    @property
    def exptime(self):
        """
        exposure time in seconds
        """
        return self._exptime

    @exptime.setter
    def exptime(self, value):
        raise RuntimeError("You should not be setting exptime on the fly; " +
                           "Just instantiate a new case of PhotometricParameters")


    @property
    def nexp(self):
        """
        number of exposures
        """
        return self._nexp

    @nexp.setter
    def nexp(self, value):
        raise RuntimeError("You should not be setting nexp on the fly; " +
                           "Just instantiate a new case of PhotometricParameters")


    @property
    def effarea(self):
        """
        effective area in cm^2
        """
        return self._effarea

    @effarea.setter
    def effarea(self, value):
        raise RuntimeError("You should not be setting effarea on the fly; " +
                           "Just instantiate a new case of PhotometricParameters")


    @property
    def gain(self):
        """
        electrons per ADU
        """
        return self._gain

    @gain.setter
    def gain(self, value):
        raise RuntimeError("You should not be setting gain on the fly; " +
                           "Just instantiate a new case of PhotometricParameters")


    @property
    def platescale(self):
        """
        arcseconds per pixel
        """
        return self._platescale

    @platescale.setter
    def platescale(self, value):
        raise RuntimeError("You should not be setting platescale on the fly; " +
                           "Just instantiate a new case of PhotometricParameters")


    @property
    def readnoise(self):
        """
        electrons per pixel per exposure
        """
        return self._readnoise

    @readnoise.setter
    def readnoise(self, value):
        raise RuntimeError("You should not be setting readnoise on the fly; " +
                           "Just instantiate a new case of PhotometricParameters")


    @property
    def darkcurrent(self):
        """
        electrons per pixel per second
        """
        return self._darkcurrent

    @darkcurrent.setter
    def darkcurrent(self, value):
        raise RuntimeError("You should not be setting darkcurrent on the fly; " +
                           "Just instantiate a new case of PhotometricParameters")


    @property
    def othernoise(self):
        """
        electrons per pixel per exposure
        """
        return self._othernoise

    @othernoise.setter
    def othernoise(self,value):
        raise RuntimeError("You should not be setting othernoise on the fly; " +
                           "Just instantiate a new case of PhotometricParameters")


    @property
    def sigmaSys(self):
        """
        systematic error in magnitudes
        """
        return self._sigmaSys


    @sigmaSys.setter
    def sigmaSys(self, value):
        raise RuntimeError("You should not be setting sigmaSys on the fly; " +
                           "Just instantiate a new case of PhotometricParameters")
