from __future__ import with_statement
import unittest
import os
import copy
import numpy
import lsst.utils.tests as utilsTests
from lsst.utils import getPackageDir

from lsst.sims.photUtils import Bandpass, Sed, BandpassDict, \
                                SedList

class BandpassDictTest(unittest.TestCase):

    def setUp(self):
        numpy.random.seed(32)
        self.bandpassPossibilities = ['u', 'g', 'r', 'i', 'z', 'y']
        self.bandpassDir = os.path.join(getPackageDir('throughputs'), 'baseline')
        self.sedDir = os.path.join(getPackageDir('sims_sed_library'))
        self.sedDir = os.path.join(self.sedDir, 'galaxySED')
        self.sedPossibilities = os.listdir(self.sedDir)


    def getListOfSedNames(self, nNames):
        return [self.sedPossibilities[ii].replace('.gz','') \
                for ii in \
                numpy.random.random_integers(0, len(self.sedPossibilities)-1, nNames)]


    def getListOfBandpasses(self, nBp):
        """
        Generate a list of nBp bandpass names and bandpasses

        Intentionally do so a nonsense order so that we can test
        that order is preserved in the BandpassDict
        """
        dexList = numpy.random.random_integers(0, len(self.bandpassPossibilities)-1, nBp)
        bandpassNameList = []
        bandpassList = []
        for dex in dexList:
            name = self.bandpassPossibilities[dex]
            bp = Bandpass()
            bp.readThroughput(os.path.join(self.bandpassDir,'total_%s.dat' % name))
            while name in bandpassNameList:
                name += '0'
            bandpassNameList.append(name)
            bandpassList.append(bp)

        return bandpassNameList, bandpassList


    def testInitialization(self):
        """
        Test that all of the member variables of BandpassDict are set
        to the correct value upon construction.
        """

        for nBp in range(3,10,1):
            nameList, bpList = self.getListOfBandpasses(nBp)
            testDict = BandpassDict(bpList, nameList)

            self.assertEqual(len(testDict), nBp)

            for controlName, testName in zip(nameList, testDict):
                self.assertEqual(controlName, testName)

            for controlName, testName in zip(nameList, testDict.keys()):
                self.assertEqual(controlName, testName)

            for name, bp in zip(nameList, bpList):
                numpy.testing.assert_array_almost_equal(bp.wavelen, testDict[name].wavelen, 10)
                numpy.testing.assert_array_almost_equal(bp.sb, testDict[name].sb, 10)

            for bpControl, bpTest in zip(bpList, testDict.values()):
                numpy.testing.assert_array_almost_equal(bpControl.wavelen, bpTest.wavelen, 10)
                numpy.testing.assert_array_almost_equal(bpControl.sb, bpTest.sb, 10)


    def testWavelenMatch(self):
        """
        Test that when you load bandpasses sampled over different
        wavelength grids, they all get sampled to the same wavelength
        grid.
        """
        dwavList = numpy.arange(5.0,25.0,5.0)
        bpList = []
        bpNameList = []
        for ix, dwav in enumerate(dwavList):
            name = 'bp_%d' % ix
            wavelen = numpy.arange(10.0, 1500.0, dwav)
            sb = numpy.exp(-0.5*(numpy.power((wavelen-100.0*ix)/100.0,2)))
            bp = Bandpass(wavelen=wavelen, sb=sb)
            bpList.append(bp)
            bpNameList.append(name)

        # First make sure that we have created distinct wavelength grids
        for ix in range(len(bpList)):
            for iy in range(ix+1,len(bpList)):
                self.assertTrue(len(bpList[ix].wavelen)!=len(bpList[iy].wavelen))

        testDict = BandpassDict(bpList, bpNameList)

        # Now make sure that the wavelength grids in the dict were resampled, but that
        # the original wavelength grids were not changed
        for ix in range(len(bpList)):
            numpy.testing.assert_array_almost_equal(testDict.values()[ix].wavelen, testDict.wavelenMatch, 19)
            if ix!=0:
                self.assertTrue(len(testDict.wavelenMatch)!=len(bpList[ix].wavelen))


    def testPhiArray(self):
        """
        Test that the phi array is correctly calculated by BandpassDict
        upon construction.
        """

        for nBp in range(3, 10, 1):
            nameList, bpList  = self.getListOfBandpasses(nBp)
            testDict = BandpassDict(bpList, nameList)
            dummySed = Sed()
            controlPhi, controlWavelenStep = dummySed.setupPhiArray(bpList)
            numpy.testing.assert_array_almost_equal(controlPhi, testDict.phiArray, 19)
            self.assertAlmostEqual(controlWavelenStep, testDict.wavelenStep, 10)


    def testExceptions(self):
        """
        Test that the correct exceptions are thrown by BandpassDict
        """

        nameList, bpList = self.getListOfBandpasses(4)
        dummyNameList = copy.deepcopy(nameList)
        dummyNameList[1] = dummyNameList[0]

        with self.assertRaises(RuntimeError) as context:
            testDict = BandpassDict(bpList, dummyNameList)

        self.assertTrue('occurs twice' in context.exception.message)


        testDict = BandpassDict(bpList, nameList)

        with self.assertRaises(AttributeError) as context:
            testDict.phiArray = None

        with self.assertRaises(AttributeError) as context:
            testDict.wavelenStep = 0.9

        with self.assertRaises(AttributeError) as context:
            testDict.wavelenMatch = numpy.arange(10.0,100.0,1.0)


    def testMagListForSed(self):
        """
        Test that magListForSed calculates the correct magnitude
        """

        wavelen = numpy.arange(10.0,2000.0,1.0)
        flux = (wavelen*2.0-5.0)*1.0e-6
        spectrum = Sed(wavelen=wavelen, flambda=flux)

        for nBp in range(3, 10, 1):

            nameList, bpList = self.getListOfBandpasses(nBp)
            testDict = BandpassDict(bpList, nameList)
            self.assertFalse(len(testDict.values()[0].wavelen)==len(spectrum.wavelen))

            magList = testDict.magListForSed(spectrum)
            for ix, (name, bp, magTest) in enumerate(zip(nameList, bpList, magList)):
                magControl = spectrum.calcMag(bp)
                self.assertAlmostEqual(magTest, magControl, 5)

    def testMagDictForSed(self):
        """
        Test that magDictForSed calculates the correct magnitude
        """

        wavelen = numpy.arange(10.0,2000.0,1.0)
        flux = (wavelen*2.0-5.0)*1.0e-6
        spectrum = Sed(wavelen=wavelen, flambda=flux)

        for nBp in range(3, 10, 1):

            nameList, bpList = self.getListOfBandpasses(nBp)
            testDict = BandpassDict(bpList, nameList)
            self.assertFalse(len(testDict.values()[0].wavelen)==len(spectrum.wavelen))

            magDict = testDict.magDictForSed(spectrum)
            for ix, (name, bp) in enumerate(zip(nameList, bpList)):
                magControl = spectrum.calcMag(bp)
                self.assertAlmostEqual(magDict[name], magControl, 5)


    def testMagListForSedList(self):
        """
        Test that magListForSedList calculates the correct magnitude
        """

        nBandpasses = 7
        bpNameList, bpList = self.getListOfBandpasses(nBandpasses)
        testBpDict = BandpassDict(bpList, bpNameList)

        nSed = 20
        sedNameList = self.getListOfSedNames(nSed)
        magNormList = numpy.random.random_sample(nSed)*5.0 + 15.0
        internalAvList = numpy.random.random_sample(nSed)*0.3 + 0.1
        redshiftList = numpy.random.random_sample(nSed)*5.0
        galacticAvList = numpy.random.random_sample(nSed)*0.3 + 0.1

        # first, test on an SedList without a wavelenMatch
        testSedList = SedList(sedNameList, magNormList,
                                    internalAvList=internalAvList,
                                    redshiftList=redshiftList,
                                    galacticAvList=galacticAvList)

        magList = testBpDict.magListForSedList(testSedList)
        self.assertEqual(magList.shape[0], nSed)
        self.assertEqual(magList.shape[1], nBandpasses)

        for ix, sedObj in enumerate(testSedList):
            dummySed = Sed(wavelen=copy.deepcopy(sedObj.wavelen),
                           flambda=copy.deepcopy(sedObj.flambda))

            for iy, bp in enumerate(testBpDict):
                mag = dummySed.calcMag(bpList[iy])
                self.assertAlmostEqual(mag, magList[ix][iy], 2)

        # now use wavelenMatch
        testSedList = SedList(sedNameList, magNormList,
                                    internalAvList=internalAvList,
                                    redshiftList=redshiftList,
                                    galacticAvList=galacticAvList,
                                    wavelenMatch=testBpDict.wavelenMatch)

        magList = testBpDict.magListForSedList(testSedList)
        self.assertEqual(magList.shape[0], nSed)
        self.assertEqual(magList.shape[1], nBandpasses)

        for ix, sedObj in enumerate(testSedList):
            dummySed = Sed(wavelen=copy.deepcopy(sedObj.wavelen),
                           flambda=copy.deepcopy(sedObj.flambda))

            for iy, bp in enumerate(testBpDict):
                mag = dummySed.calcMag(bpList[iy])
                self.assertAlmostEqual(mag, magList[ix][iy], 2)


    def testMagArrayForSedList(self):
        """
        Test that magArrayForSedList calculates the correct magnitude
        """

        nBandpasses = 7
        bpNameList, bpList = self.getListOfBandpasses(nBandpasses)
        testBpDict = BandpassDict(bpList, bpNameList)

        nSed = 20
        sedNameList = self.getListOfSedNames(nSed)
        magNormList = numpy.random.random_sample(nSed)*5.0 + 15.0
        internalAvList = numpy.random.random_sample(nSed)*0.3 + 0.1
        redshiftList = numpy.random.random_sample(nSed)*5.0
        galacticAvList = numpy.random.random_sample(nSed)*0.3 + 0.1

        # first, test on an SedList without a wavelenMatch
        testSedList = SedList(sedNameList, magNormList,
                                    internalAvList=internalAvList,
                                    redshiftList=redshiftList,
                                    galacticAvList=galacticAvList)

        magArray = testBpDict.magArrayForSedList(testSedList)

        for ix, sedObj in enumerate(testSedList):
            dummySed = Sed(wavelen=copy.deepcopy(sedObj.wavelen),
                           flambda=copy.deepcopy(sedObj.flambda))

            for iy, bp in enumerate(bpNameList):
                mag = dummySed.calcMag(bpList[iy])
                self.assertAlmostEqual(mag, magArray[bp][ix], 2)

        # now use wavelenMatch
        testSedList = SedList(sedNameList, magNormList,
                                    internalAvList=internalAvList,
                                    redshiftList=redshiftList,
                                    galacticAvList=galacticAvList,
                                    wavelenMatch=testBpDict.wavelenMatch)

        magArray = testBpDict.magArrayForSedList(testSedList)

        for ix, sedObj in enumerate(testSedList):
            dummySed = Sed(wavelen=copy.deepcopy(sedObj.wavelen),
                           flambda=copy.deepcopy(sedObj.flambda))

            for iy, bp in enumerate(bpNameList):
                mag = dummySed.calcMag(bpList[iy])
                self.assertAlmostEqual(mag, magArray[bp][ix], 2)



    def testIndicesOnMagnitudes(self):
        """
        Test that, when you pass a list of indices into the calcMagList
        methods, you get the correct magnitudes out.
        """

        nBandpasses = 7
        nameList, bpList = self.getListOfBandpasses(nBandpasses)
        testBpDict = BandpassDict(bpList, nameList)

        # first try it with a single Sed
        wavelen = numpy.arange(10.0,2000.0,1.0)
        flux = (wavelen*2.0-5.0)*1.0e-6
        spectrum = Sed(wavelen=wavelen, flambda=flux)
        indices = [1,2,5]

        magList = testBpDict.magListForSed(spectrum, indices=indices)
        ctNaN = 0
        for ix, (name, bp, magTest) in enumerate(zip(nameList, bpList, magList)):
            if ix in indices:
                magControl = spectrum.calcMag(bp)
                self.assertAlmostEqual(magTest, magControl, 5)
            else:
                ctNaN += 1
                self.assertTrue(numpy.isnan(magTest))

        self.assertEqual(ctNaN, 4)

        nSed = 20
        sedNameList = self.getListOfSedNames(nSed)
        magNormList = numpy.random.random_sample(nSed)*5.0 + 15.0
        internalAvList = numpy.random.random_sample(nSed)*0.3 + 0.1
        redshiftList = numpy.random.random_sample(nSed)*5.0
        galacticAvList = numpy.random.random_sample(nSed)*0.3 + 0.1

        # now try a SedList without a wavelenMatch
        testSedList = SedList(sedNameList, magNormList,
                                    internalAvList=internalAvList,
                                    redshiftList=redshiftList,
                                    galacticAvList=galacticAvList)

        magList = testBpDict.magListForSedList(testSedList, indices=indices)
        self.assertEqual(magList.shape[0], nSed)
        self.assertEqual(magList.shape[1], nBandpasses)

        for ix, sedObj in enumerate(testSedList):
            dummySed = Sed(wavelen=copy.deepcopy(sedObj.wavelen),
                           flambda=copy.deepcopy(sedObj.flambda))

            ctNaN = 0
            for iy, bp in enumerate(testBpDict):
                if iy in indices:
                    mag = dummySed.calcMag(testBpDict[bp])
                    self.assertAlmostEqual(mag, magList[ix][iy], 2)
                else:
                    ctNaN += 1
                    self.assertTrue(numpy.isnan(magList[ix][iy]))

            self.assertEqual(ctNaN, 4)

        # now use wavelenMatch
        testSedList = SedList(sedNameList, magNormList,
                                    internalAvList=internalAvList,
                                    redshiftList=redshiftList,
                                    galacticAvList=galacticAvList,
                                    wavelenMatch=testBpDict.wavelenMatch)

        magList = testBpDict.magListForSedList(testSedList, indices=indices)
        self.assertEqual(magList.shape[0], nSed)
        self.assertEqual(magList.shape[1], nBandpasses)

        for ix, sedObj in enumerate(testSedList):
            dummySed = Sed(wavelen=copy.deepcopy(sedObj.wavelen),
                           flambda=copy.deepcopy(sedObj.flambda))

            ctNaN = 0
            for iy, bp in enumerate(testBpDict):
                if iy in indices:
                    mag = dummySed.calcMag(testBpDict[bp])
                    self.assertAlmostEqual(mag, magList[ix][iy], 2)
                else:
                    ctNaN +=  1
                    self.assertTrue(numpy.isnan(magList[ix][iy]))

            self.assertEqual(ctNaN, 4)


    def testFluxListForSed(self):
        """
        Test that fluxListForSed calculates the correct fluxes
        """

        wavelen = numpy.arange(10.0,2000.0,1.0)
        flux = (wavelen*2.0-5.0)*1.0e-6
        spectrum = Sed(wavelen=wavelen, flambda=flux)

        for nBp in range(3, 10, 1):

            nameList, bpList = self.getListOfBandpasses(nBp)
            testDict = BandpassDict(bpList, nameList)
            self.assertFalse(len(testDict.values()[0].wavelen)==len(spectrum.wavelen))

            fluxList = testDict.fluxListForSed(spectrum)
            for ix, (name, bp, fluxTest) in enumerate(zip(nameList, bpList, fluxList)):
                fluxControl = spectrum.calcFlux(bp)
                self.assertAlmostEqual(fluxTest/fluxControl, 1.0, 2)


    def testFluxDictForSed(self):
        """
        Test that fluxDictForSed calculates the correct fluxes
        """

        wavelen = numpy.arange(10.0,2000.0,1.0)
        flux = (wavelen*2.0-5.0)*1.0e-6
        spectrum = Sed(wavelen=wavelen, flambda=flux)

        for nBp in range(3, 10, 1):

            nameList, bpList = self.getListOfBandpasses(nBp)
            testDict = BandpassDict(bpList, nameList)
            self.assertFalse(len(testDict.values()[0].wavelen)==len(spectrum.wavelen))

            fluxDict = testDict.fluxDictForSed(spectrum)
            for ix, (name, bp) in enumerate(zip(nameList, bpList)):
                fluxControl = spectrum.calcFlux(bp)
                self.assertAlmostEqual(fluxDict[name]/fluxControl, 1.0, 2)



    def testFluxListForSedList(self):
        """
        Test that fluxListForSedList calculates the correct fluxes
        """

        nBandpasses = 7
        bpNameList, bpList = self.getListOfBandpasses(nBandpasses)
        testBpDict = BandpassDict(bpList, bpNameList)

        nSed = 20
        sedNameList = self.getListOfSedNames(nSed)
        magNormList = numpy.random.random_sample(nSed)*5.0 + 15.0
        internalAvList = numpy.random.random_sample(nSed)*0.3 + 0.1
        redshiftList = numpy.random.random_sample(nSed)*5.0
        galacticAvList = numpy.random.random_sample(nSed)*0.3 + 0.1

        # first, test on an SedList without a wavelenMatch
        testSedList = SedList(sedNameList, magNormList,
                                    internalAvList=internalAvList,
                                    redshiftList=redshiftList,
                                    galacticAvList=galacticAvList)

        fluxList = testBpDict.fluxListForSedList(testSedList)
        self.assertEqual(fluxList.shape[0], nSed)
        self.assertEqual(fluxList.shape[1], nBandpasses)

        for ix, sedObj in enumerate(testSedList):
            dummySed = Sed(wavelen=copy.deepcopy(sedObj.wavelen),
                           flambda=copy.deepcopy(sedObj.flambda))

            for iy, bp in enumerate(testBpDict):
                flux = dummySed.calcFlux(bpList[iy])
                self.assertAlmostEqual(flux/fluxList[ix][iy], 1.0, 2)

        # now use wavelenMatch
        testSedList = SedList(sedNameList, magNormList,
                                    internalAvList=internalAvList,
                                    redshiftList=redshiftList,
                                    galacticAvList=galacticAvList,
                                    wavelenMatch=testBpDict.wavelenMatch)

        fluxList = testBpDict.fluxListForSedList(testSedList)
        self.assertEqual(fluxList.shape[0], nSed)
        self.assertEqual(fluxList.shape[1], nBandpasses)

        for ix, sedObj in enumerate(testSedList):
            dummySed = Sed(wavelen=copy.deepcopy(sedObj.wavelen),
                           flambda=copy.deepcopy(sedObj.flambda))

            for iy, bp in enumerate(testBpDict):
                flux = dummySed.calcFlux(bpList[iy])
                self.assertAlmostEqual(flux/fluxList[ix][iy], 1.0, 2)


    def testFluxArrayForSedList(self):
        """
        Test that fluxArrayForSedList calculates the correct fluxes
        """

        nBandpasses = 7
        bpNameList, bpList = self.getListOfBandpasses(nBandpasses)
        testBpDict = BandpassDict(bpList, bpNameList)

        nSed = 20
        sedNameList = self.getListOfSedNames(nSed)
        magNormList = numpy.random.random_sample(nSed)*5.0 + 15.0
        internalAvList = numpy.random.random_sample(nSed)*0.3 + 0.1
        redshiftList = numpy.random.random_sample(nSed)*5.0
        galacticAvList = numpy.random.random_sample(nSed)*0.3 + 0.1

        # first, test on an SedList without a wavelenMatch
        testSedList = SedList(sedNameList, magNormList,
                                    internalAvList=internalAvList,
                                    redshiftList=redshiftList,
                                    galacticAvList=galacticAvList)

        fluxArray = testBpDict.fluxArrayForSedList(testSedList)

        for ix, sedObj in enumerate(testSedList):
            dummySed = Sed(wavelen=copy.deepcopy(sedObj.wavelen),
                           flambda=copy.deepcopy(sedObj.flambda))

            for iy, bp in enumerate(bpNameList):
                flux = dummySed.calcFlux(bpList[iy])
                self.assertAlmostEqual(flux/fluxArray[bp][ix], 1.0, 2)

        # now use wavelenMatch
        testSedList = SedList(sedNameList, magNormList,
                                    internalAvList=internalAvList,
                                    redshiftList=redshiftList,
                                    galacticAvList=galacticAvList,
                                    wavelenMatch=testBpDict.wavelenMatch)

        fluxArray = testBpDict.fluxArrayForSedList(testSedList)

        for ix, sedObj in enumerate(testSedList):
            dummySed = Sed(wavelen=copy.deepcopy(sedObj.wavelen),
                           flambda=copy.deepcopy(sedObj.flambda))

            for iy, bp in enumerate(bpNameList):
                flux = dummySed.calcFlux(bpList[iy])
                self.assertAlmostEqual(flux/fluxArray[bp][ix], 1.0, 2)



    def testIndicesOnFlux(self):
        """
        Test that, when you pass a list of indices into the calcFluxList
        methods, you get the correct fluxes out.
        """

        nBandpasses = 7
        nameList, bpList = self.getListOfBandpasses(nBandpasses)
        testBpDict = BandpassDict(bpList, nameList)

        # first try it with a single Sed
        wavelen = numpy.arange(10.0,2000.0,1.0)
        flux = (wavelen*2.0-5.0)*1.0e-6
        spectrum = Sed(wavelen=wavelen, flambda=flux)
        indices = [1,2,5]

        fluxList = testBpDict.fluxListForSed(spectrum, indices=indices)
        ctNaN = 0
        for ix, (name, bp, fluxTest) in enumerate(zip(nameList, bpList, fluxList)):
            if ix in indices:
                fluxControl = spectrum.calcFlux(bp)
                self.assertAlmostEqual(fluxTest/fluxControl, 1.0, 2)
            else:
                ctNaN += 1
                self.assertTrue(numpy.isnan(fluxTest))

        self.assertEqual(ctNaN, 4)

        nSed = 20
        sedNameList = self.getListOfSedNames(nSed)
        magNormList = numpy.random.random_sample(nSed)*5.0 + 15.0
        internalAvList = numpy.random.random_sample(nSed)*0.3 + 0.1
        redshiftList = numpy.random.random_sample(nSed)*5.0
        galacticAvList = numpy.random.random_sample(nSed)*0.3 + 0.1

        # now try a SedList without a wavelenMatch
        testSedList = SedList(sedNameList, magNormList,
                                    internalAvList=internalAvList,
                                    redshiftList=redshiftList,
                                    galacticAvList=galacticAvList)

        fluxList = testBpDict.fluxListForSedList(testSedList, indices=indices)
        self.assertEqual(fluxList.shape[0], nSed)
        self.assertEqual(fluxList.shape[1], nBandpasses)

        for ix, sedObj in enumerate(testSedList):
            dummySed = Sed(wavelen=copy.deepcopy(sedObj.wavelen),
                           flambda=copy.deepcopy(sedObj.flambda))

            ctNaN = 0
            for iy, bp in enumerate(testBpDict):
                if iy in indices:
                    flux = dummySed.calcFlux(testBpDict[bp])
                    self.assertAlmostEqual(flux/fluxList[ix][iy], 1.0, 2)
                else:
                    ctNaN += 1
                    self.assertTrue(numpy.isnan(fluxList[ix][iy]))

            self.assertEqual(ctNaN, 4)

        # now use wavelenMatch
        testSedList = SedList(sedNameList, magNormList,
                                    internalAvList=internalAvList,
                                    redshiftList=redshiftList,
                                    galacticAvList=galacticAvList,
                                    wavelenMatch=testBpDict.wavelenMatch)

        fluxList = testBpDict.fluxListForSedList(testSedList, indices=indices)
        self.assertEqual(fluxList.shape[0], nSed)
        self.assertEqual(fluxList.shape[1], nBandpasses)

        for ix, sedObj in enumerate(testSedList):
            dummySed = Sed(wavelen=copy.deepcopy(sedObj.wavelen),
                           flambda=copy.deepcopy(sedObj.flambda))

            ctNaN = 0
            for iy, bp in enumerate(testBpDict):
                if iy in indices:
                    flux = dummySed.calcFlux(testBpDict[bp])
                    self.assertAlmostEqual(flux/fluxList[ix][iy], 1.0, 2)
                else:
                    ctNaN +=  1
                    self.assertTrue(numpy.isnan(fluxList[ix][iy]))

            self.assertEqual(ctNaN, 4)


    def testLoadTotalBandpassesFromFiles(self):
        """
        Test that the class method loadTotalBandpassesFromFiles produces the
        expected result
        """

        bandpassDir = os.path.join(getPackageDir('sims_photUtils'), 'tests', 'cartoonSedTestData')
        bandpassNames = ['g', 'r', 'u']
        bandpassRoot = 'test_bandpass_'

        bandpassDict = BandpassDict.loadTotalBandpassesFromFiles(bandpassNames=bandpassNames,
                                                                 bandpassDir=bandpassDir,
                                                                 bandpassRoot = bandpassRoot)

        controlBandpassList = []
        for bpn in bandpassNames:
            dummyBp = Bandpass()
            dummyBp.readThroughput(os.path.join(bandpassDir,bandpassRoot+bpn+'.dat'))
            controlBandpassList.append(dummyBp)

        wMin = controlBandpassList[0].wavelen[0]
        wMax = controlBandpassList[0].wavelen[-1]
        wStep = controlBandpassList[0].wavelen[1]-controlBandpassList[0].wavelen[0]

        for bp in controlBandpassList:
            bp.resampleBandpass(wavelen_min=wMin, wavelen_max=wMax, wavelen_step=wStep)

        for test, control in zip(bandpassDict.values(), controlBandpassList):
            numpy.testing.assert_array_almost_equal(test.wavelen, control.wavelen, 19)
            numpy.testing.assert_array_almost_equal(test.sb, control.sb, 19)


    def testLoadBandpassesFromFiles(self):
        """
        Test that running the classmethod loadBandpassesFromFiles produces
        expected result
        """

        fileDir = os.path.join(getPackageDir('sims_photUtils'), 'tests', 'cartoonSedTestData')
        bandpassNames = ['g', 'z', 'i']
        bandpassRoot='test_bandpass_'
        componentList = ['toy_mirror.dat']
        atmo = os.path.join(fileDir, 'toy_atmo.dat')

        bandpassDict, hardwareDict = BandpassDict.loadBandpassesFromFiles(bandpassNames=bandpassNames,
                                                                          filedir=fileDir,
                                                                          bandpassRoot=bandpassRoot,
                                                                          componentList=componentList,
                                                                          atmoTransmission=atmo)

        controlBandpassList = []
        controlHardwareList = []

        for bpn in bandpassNames:
            componentList = [os.path.join(fileDir, bandpassRoot+bpn+'.dat'),
                             os.path.join(fileDir, 'toy_mirror.dat')]

            dummyBp = Bandpass()
            dummyBp.readThroughputList(componentList)
            controlHardwareList.append(dummyBp)

            componentList = [os.path.join(fileDir, bandpassRoot+bpn+'.dat'),
                             os.path.join(fileDir, 'toy_mirror.dat'),
                             os.path.join(fileDir, 'toy_atmo.dat')]

            dummyBp = Bandpass()
            dummyBp.readThroughputList(componentList)
            controlBandpassList.append(dummyBp)


        wMin = controlBandpassList[0].wavelen[0]
        wMax = controlBandpassList[0].wavelen[-1]
        wStep = controlBandpassList[0].wavelen[1]-controlBandpassList[0].wavelen[0]

        for bp, hh in zip(controlBandpassList, controlHardwareList):
            bp.resampleBandpass(wavelen_min=wMin, wavelen_max=wMax, wavelen_step=wStep)
            hh.resampleBandpass(wavelen_min=wMin, wavelen_max=wMax, wavelen_step=wStep)

        for test, control in zip(bandpassDict.values(), controlBandpassList):
            numpy.testing.assert_array_almost_equal(test.wavelen, control.wavelen, 19)
            numpy.testing.assert_array_almost_equal(test.sb, control.sb, 19)

        for test, control in zip(hardwareDict.values(), controlHardwareList):
            numpy.testing.assert_array_almost_equal(test.wavelen, control.wavelen, 19)
            numpy.testing.assert_array_almost_equal(test.sb, control.sb, 19)


def suite():
    utilsTests.init()
    suites = []
    suites += unittest.makeSuite(BandpassDictTest)
    return unittest.TestSuite(suites)

def run(shouldExit = False):
    utilsTests.run(suite(),shouldExit)

if __name__ == "__main__":
    run(True)
