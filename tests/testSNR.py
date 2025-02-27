import os
import numpy
import unittest
import lsst.utils
import lsst.utils.tests as utilsTests
from lsst.sims.utils import ObservationMetaData
import lsst.sims.photUtils.SignalToNoise as snr
from lsst.sims.photUtils import Sed, Bandpass, PhotometricParameters, \
                                LSSTdefaults
from lsst.sims.photUtils.utils import setM5

class TestSNRmethods(unittest.TestCase):


    def setUp(self):

        starFileName = os.path.join(lsst.utils.getPackageDir('sims_sed_library'),'starSED')
        starFileName = os.path.join(starFileName, 'kurucz','km20_5750.fits_g40_5790.gz')
        starName = os.path.join(lsst.utils.getPackageDir('sims_sed_library'),starFileName)
        self.starSED = Sed()
        self.starSED.readSED_flambda(starName)
        imsimband = Bandpass()
        imsimband.imsimBandpass()
        fNorm = self.starSED.calcFluxNorm(22.0, imsimband)
        self.starSED.multiplyFluxNorm(fNorm)

        hardwareDir = os.path.join(lsst.utils.getPackageDir('throughputs'),'baseline')
        componentList = ['detector.dat', 'm1.dat', 'm2.dat', 'm3.dat',
                         'lens1.dat', 'lens2.dat', 'lens3.dat']
        self.skySed = Sed()
        self.skySed.readSED_flambda(os.path.join(hardwareDir,'darksky.dat'))

        totalNameList = ['total_u.dat', 'total_g.dat', 'total_r.dat', 'total_i.dat',
                         'total_z.dat', 'total_y.dat']

        self.bpList = []
        self.hardwareList = []
        for name in totalNameList:
            dummy = Bandpass()
            dummy.readThroughput(os.path.join(hardwareDir, name))
            self.bpList.append(dummy)

            dummy = Bandpass()
            hardwareNameList = [os.path.join(hardwareDir, name)]
            for component in componentList:
                hardwareNameList.append(os.path.join(hardwareDir, component))
            dummy.readThroughputList(hardwareNameList)
            self.hardwareList.append(dummy)

        self.filterNameList = ['u', 'g', 'r', 'i', 'z', 'y']

    def testMagError(self):
        """
        Make sure that calcMagError_sed and calcMagError_m5
        agree to within 0.001
        """
        defaults = LSSTdefaults()
        photParams = PhotometricParameters()

        #create a cartoon spectrum to test on
        spectrum = Sed()
        spectrum.setFlatSED()
        spectrum.multiplyFluxNorm(1.0e-9)

        #find the magnitudes of that spectrum in our bandpasses
        magList = []
        for total in self.bpList:
            magList.append(spectrum.calcMag(total))
        magList = numpy.array(magList)

        #try for different normalizations of the skySED
        for fNorm in numpy.arange(1.0, 5.0, 1.0):
            self.skySed.multiplyFluxNorm(fNorm)

            for total, hardware, filterName, mm in \
            zip(self.bpList, self.hardwareList, self.filterNameList, magList):

                FWHMeff = defaults.FWHMeff(filterName)

                m5 = snr.calcM5(self.skySed, total, hardware, photParams, FWHMeff=FWHMeff)

                sigma_sed = snr.calcMagError_sed(spectrum, total, self.skySed,
                                                   hardware, photParams, FWHMeff=FWHMeff)

                sigma_m5, gamma = snr.calcMagError_m5(mm, total, m5, photParams)

                self.assertAlmostEqual(sigma_m5, sigma_sed, 3)


    def testVerboseSNR(self):
        """
        Make sure that calcSNR_sed has everything it needs to run in verbose mode
        """
        defaults = LSSTdefaults()
        photParams = PhotometricParameters()

        #create a cartoon spectrum to test on
        spectrum = Sed()
        spectrum.setFlatSED()
        spectrum.multiplyFluxNorm(1.0e-9)

        snr.calcSNR_sed(spectrum, self.bpList[0], self.skySed,
                        self.hardwareList[0], photParams, FWHMeff=0.7, verbose=True)


    def testSignalToNoise(self):
        """
        Test that calcSNR_m5 and calcSNR_sed give similar results
        """
        defaults = LSSTdefaults()
        photParams = PhotometricParameters()

        m5 = []
        for i in range(len(self.hardwareList)):
            m5.append(snr.calcM5(self.skySed, self.bpList[i],
                      self.hardwareList[i],
                      photParams, FWHMeff=defaults.FWHMeff(self.filterNameList[i])))


        sedDir = lsst.utils.getPackageDir('sims_sed_library')
        sedDir = os.path.join(sedDir, 'starSED', 'kurucz')
        fileNameList = os.listdir(sedDir)

        numpy.random.seed(42)
        offset = numpy.random.random_sample(len(fileNameList))*2.0

        for ix, name in enumerate(fileNameList):
            if ix>100:
                break
            spectrum = Sed()
            spectrum.readSED_flambda(os.path.join(sedDir, name))
            ff = spectrum.calcFluxNorm(m5[2]-offset[ix], self.bpList[2])
            spectrum.multiplyFluxNorm(ff)
            for i in range(len(self.bpList)):
                control_snr = snr.calcSNR_sed(spectrum, self.bpList[i],
                                              self.skySed,
                                              self.hardwareList[i],
                                              photParams, defaults.FWHMeff(self.filterNameList[i]))

                mag = spectrum.calcMag(self.bpList[i])

                test_snr, gamma = snr.calcSNR_m5(mag, self.bpList[i], m5[i], photParams)
                self.assertLess((test_snr-control_snr)/control_snr, 0.001)




    def testSystematicUncertainty(self):
        """
        Test that systematic uncertainty is added correctly.
        """
        sigmaSys = 0.002
        m5_list = [23.5, 24.3, 22.1, 20.0, 19.5, 21.7]
        photParams= PhotometricParameters(sigmaSys=sigmaSys)

        obs_metadata = ObservationMetaData(pointingRA=23.0, pointingDec=45.0,
                                           m5=m5_list, bandpassName=self.filterNameList)
        magnitude_list = []
        for bp in self.bpList:
            mag = self.starSED.calcMag(bp)
            magnitude_list.append(mag)

        skySedList = []

        for bp, hardware, filterName, mm, m5 in \
            zip(self.bpList, self.hardwareList, self.filterNameList, magnitude_list, m5_list):

            skyDummy = Sed()
            skyDummy.readSED_flambda(os.path.join(lsst.utils.getPackageDir('throughputs'),
                                     'baseline', 'darksky.dat'))

            normalizedSkyDummy = setM5(obs_metadata.m5[filterName], skyDummy,
                                       bp, hardware,
                                       FWHMeff=LSSTdefaults().FWHMeff(filterName),
                                       photParams=photParams)


            sigma, gamma = snr.calcMagError_m5(mm, bp, m5, photParams)

            snrat = snr.calcSNR_sed(self.starSED, bp, normalizedSkyDummy, hardware,
                                  FWHMeff=LSSTdefaults().FWHMeff(filterName),
                                  photParams=PhotometricParameters())

            testSNR, gamma = snr.calcSNR_m5(mm, bp, m5, photParams=PhotometricParameters(sigmaSys=0.0))

            self.assertAlmostEqual(snrat, testSNR, 10, msg = 'failed on calcSNR_m5 test %e != %e ' \
                                                               % (snrat, testSNR))

            control = numpy.sqrt(numpy.power(snr.magErrorFromSNR(testSNR),2) + numpy.power(sigmaSys,2))

            msg = '%e is not %e; failed' % (sigma, control)

            self.assertAlmostEqual(sigma, control, 10, msg=msg)


    def testNoSystematicUncertainty(self):
        """
        Test that systematic uncertainty is handled correctly when set to None.
        """
        m5_list = [23.5, 24.3, 22.1, 20.0, 19.5, 21.7]
        photParams= PhotometricParameters(sigmaSys=0.0)

        obs_metadata = ObservationMetaData(pointingRA=23.0, pointingDec=45.0,
                                           m5=m5_list, bandpassName=self.filterNameList)

        magnitude_list = []
        for bp in self.bpList:
            mag = self.starSED.calcMag(bp)
            magnitude_list.append(mag)

        skySedList = []

        for bp, hardware, filterName, mm, m5 in \
            zip(self.bpList, self.hardwareList, self.filterNameList, magnitude_list, m5_list):

            skyDummy = Sed()
            skyDummy.readSED_flambda(os.path.join(lsst.utils.getPackageDir('throughputs'),
                                     'baseline', 'darksky.dat'))

            normalizedSkyDummy = setM5(obs_metadata.m5[filterName], skyDummy,
                                       bp, hardware,
                                       FWHMeff=LSSTdefaults().FWHMeff(filterName),
                                       photParams=photParams)

            sigma, gamma = snr.calcMagError_m5(mm, bp, m5, photParams)


            snrat = snr.calcSNR_sed(self.starSED, bp, normalizedSkyDummy, hardware,
                              FWHMeff=LSSTdefaults().FWHMeff(filterName),
                              photParams=PhotometricParameters())

            testSNR, gamma = snr.calcSNR_m5(mm, bp, m5, photParams=PhotometricParameters(sigmaSys=0.0))

            self.assertAlmostEqual(snrat, testSNR, 10, msg = 'failed on calcSNR_m5 test %e != %e ' \
                                                               % (snrat, testSNR))

            control = snr.magErrorFromSNR(testSNR)

            msg = '%e is not %e; failed' % (sigma, control)

            self.assertAlmostEqual(sigma, control, 10, msg=msg)

    def testFWHMconversions(self):
        FWHMeff = 0.8
        FWHMgeom = snr.FWHMeff2FWHMgeom(FWHMeff)
        self.assertEqual(FWHMgeom, (0.822*FWHMeff+0.052))
        FWHMgeom = 0.8
        FWHMeff = snr.FWHMgeom2FWHMeff(FWHMgeom)
        self.assertEqual(FWHMeff, (FWHMgeom-0.052)/0.822)


    def testSNR_arr(self):
        """
        Test that calcSNR_m5 works on numpy arrays of magnitudes
        """
        numpy.random.seed(17)
        mag_list = numpy.random.random_sample(100)*5.0 + 15.0

        photParams = PhotometricParameters()
        bp = self.bpList[0]
        m5 = 24.0
        control_list = []
        for mm in mag_list:
            ratio, gamma = snr.calcSNR_m5(mm, bp, m5, photParams)
            control_list.append(ratio)
        control_list = numpy.array(control_list)

        test_list, gamma = snr.calcSNR_m5(mag_list, bp, m5, photParams)

        numpy.testing.assert_array_equal(control_list, test_list)


    def testError_arr(self):
        """
        Test that calcMagError_m5 works on numpy arrays of magnitudes
        """
        numpy.random.seed(17)
        mag_list = numpy.random.random_sample(100)*5.0 + 15.0

        photParams = PhotometricParameters()
        bp = self.bpList[0]
        m5 = 24.0
        control_list = []
        for mm in mag_list:
            sig, gamma = snr.calcMagError_m5(mm, bp, m5, photParams)
            control_list.append(sig)
        control_list = numpy.array(control_list)

        test_list, gamma = snr.calcMagError_m5(mag_list, bp, m5, photParams)

        numpy.testing.assert_array_equal(control_list, test_list)


def suite():
    utilsTests.init()
    suites = []
    suites += unittest.makeSuite(TestSNRmethods)
    return unittest.TestSuite(suites)

def run(shouldExit = False):
    utilsTests.run(suite(),shouldExit)

if __name__ == "__main__":
    run(True)
