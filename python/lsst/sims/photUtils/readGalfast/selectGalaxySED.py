import os
import numpy as np
import eups

from lsst.sims.photUtils.Sed import Sed
from lsst.sims.photUtils.readGalfast.rgUtils import rgGalaxy
from lsst.sims.photUtils.Photometry import PhotometryBase as phot
from lsst.sims.photUtils.EBV import EBVbase as ebv

__all__ = ["selectGalaxySED"]

class selectGalaxySED(rgGalaxy):

    def matchToRestFrame(self, sedList, catMags, bandpassList = None, magNormAcc = 2):

        """
        This will find the closest match to the magnitudes of a galaxy catalog if those magnitudes are in
        the rest frame.

        @param [in] sedList is the set of spectral objects from the models SEDs provided by loadBC03
        or other custom loader routine.

        @param [in] catMags is an array of the magnitudes of catalog objects to be matched with a model SED.
        It should be organized so that there is one object's magnitudes along each row.

        @param [in] bandpassList is a list of bandpass objects with which to calculate magnitudes. If left
        equal to None it will by default load the SDSS [u,g,r,i,z] bandpasses.
        
        @param [in] magNormAcc is the number of decimal places within the magNorm result will be accurate.

        @param [out] sedMatches is a list with the name of a model SED that matches most closely to each
        object in the catalog.
        """

        #Set up photometry to calculate model Mags
        galPhot = phot()
        if bandpassList is None:
            galPhot.loadBandPassesFromFiles(['u','g','r','i','z'], 
                                            bandPassDir = os.path.join(eups.productDir('throughputs'),'sdss'),
                                            bandPassRoot = 'sdss_')
        else:
            galPhot.bandPassList = bandpassList
        galPhot.setupPhiArray_dict()

        modelColors = []
        sedMatches = []
        magNormMatches = []

        #Find the colors for all model SEDs
        modelColors = self.calcBasicColors(sedList, galPhot)

        #Match the catalog colors to models
        numCatMags = len(catMags)
        numOn = 0
        matchColors = []

        for filtNum in range(0, len(galPhot.bandPassList)-1):
            matchColors.append(np.transpose(catMags)[filtNum] - np.transpose(catMags)[filtNum+1])

        matchColors = np.transpose(matchColors)

        for catObject in matchColors:
            if numOn % 10000 == 0:
                print 'Matched %i of %i catalog objects to SEDs' % (numOn, numCatMags)
            distanceArray = np.zeros(len(sedList))
            for filtNum in range(0, len(galPhot.bandPassList)-1):
                distanceArray += np.power((modelColors[filtNum] - catObject[filtNum]),2)
            matchedSEDNum = np.nanargmin(distanceArray)
            sedMatches.append(sedList[matchedSEDNum].name)
            magNorm = self.calcMagNorm(catMags[numOn], sedList[matchedSEDNum], 
                                       galPhot, stepSize = np.power(10, -float(magNormAcc)))
            magNormMatches.append(magNorm)
            numOn += 1

        print 'Done Matching. Matched %i catalog objects to SEDs' % (numCatMags)
            
        return sedMatches, magNormMatches

    def matchToObserved(self, sedList, catRA, catDec, catRedshifts, catMags, 
                        bandpassList = None, dzAcc = 2, magNormAcc = 2, extinction = True,
                        extCoeffs = (4.239, 3.303, 2.285, 1.698, 1.263)):

        """
        This will find the closest match to the magnitudes of a galaxy catalog if those magnitudes are in
        the observed frame and can correct for extinction from within the milky way as well if needed.
        In order to make things faster it first calculates colors for all model SEDs at redshifts between
        the minimum and maximum redshifts of the catalog objects provided with a grid spacing in redshift
        defined by the parameter dzAcc.

        @param [in] sedList is the set of spectral objects from the models SEDs provided by loadBC03
        or other custom loader routine.

        @param [in] catRA is an array of the RA positions for each catalog object.

        @param [in] catDec is an array of the Dec position for each catalog object.

        @param [in] catRedshifts is an array of the redshifts of each catalog object.

        @param [in] catMags is an array of the magnitudes of catalog objects to be matched with a model SED.
        It should be organized so that there is one object's magnitudes along each row.

        @param [in] bandpassList is a list of bandpass objects with which to calculate magnitudes. If left
        equal to None it will by default load the SDSS [u,g,r,i,z] bandpasses and therefore agree with 
        default extCoeffs.

        @param [in] dzAcc is the number of decimal places you want to use when building the redshift grid.
        For example, dzAcc = 2 will create a grid between the minimum and maximum redshifts with colors
        calculated at every 0.01 change in redshift.
        
        @param [in] magNormAcc is the number of decimal places within the magNorm result will be accurate.

        @param [in] extinction is a boolean that determines whether to correct catalog magnitudes for 
        dust in the milky way. This uses calculateEBV from EBV.py to find an EBV value for the object's
        ra and dec coordinates and then uses the coefficients provided by extCoeffs which should come
        from Schlafly and Finkbeiner (2011) for the correct filters and in the same order as provided
        in bandpassList.

        @param [in] extCoeffs are the Schlafly and Finkbeiner (2011) coefficients for the given filters
        from bandpassList and need to be in the same order as bandpassList. The default given are the SDSS
        [u,g,r,i,z] values.

        @param [out] sedMatches is a list with the name of a model SED that matches most closely to each
        object in the catalog.
        """

        #Set up photometry to calculate model Mags
        galPhot = phot()
        if bandpassList is None:
            galPhot.loadBandPassesFromFiles(['u','g','r','i','z'], 
                                            bandPassDir = os.path.join(eups.productDir('throughputs'),'sdss'),
                                            bandPassRoot = 'sdss_')
        else:
            galPhot.bandPassList = bandpassList
        galPhot.setupPhiArray_dict()
        
        #Calculate ebv from ra, dec coordinates if needed
        if extinction == True:
            calcEBV = ebv()
            raDec = np.array((catRA,catDec))
            #If only matching one object need to reshape for calculateEbv
            if len(raDec.shape) == 1:
                raDec = raDec.reshape((2,1))
            ebvVals = calcEBV.calculateEbv(equatorialCoordinates = raDec)
            objMags = self.deReddenMags(ebvVals, catMags, extCoeffs)
        else:
            objMags = catMags

        minRedshift = np.round(np.min(catRedshifts), dzAcc)
        maxRedshift = np.round(np.max(catRedshifts), dzAcc)
        dz = np.power(10., (-1*dzAcc))

        redshiftRange = np.round(np.arange(minRedshift - dz, maxRedshift + (2*dz), dz), dzAcc)
        numRedshifted = 0
        sedMatches = [None] * len(catRedshifts)
        magNormMatches = [None] * len(catRedshifts)
        redshiftIndex = np.argsort(catRedshifts)

        numOn = 0
        lastRedshift = -100
        print 'Starting Matching. Arranged by redshift value.'
        for redshift in redshiftRange:

            if numRedshifted % 10 == 0:
                print '%i out of %i redshifts gone through' % (numRedshifted, len(redshiftRange))
            numRedshifted += 1

            colorSet = []
            for galSpec in sedList:
                sedColors = []
                fileSED = Sed()
                fileSED.setSED(wavelen = galSpec.wavelen, flambda = galSpec.flambda)
                fileSED.redshiftSED(redshift)
                sEDMags = galPhot.manyMagCalc_list(fileSED)
                for filtNum in range(0, len(galPhot.bandPassList)-1):
                    sedColors.append(sEDMags[filtNum] - sEDMags[filtNum+1])
                colorSet.append(sedColors)
            colorSet = np.transpose(colorSet)
            for currentIndex in redshiftIndex[numOn:]:
                matchMags = objMags[currentIndex]
                if lastRedshift < np.round(catRedshifts[currentIndex],dzAcc) <= redshift:
                    for filtNum in range(0, len(galPhot.bandPassList)-1):
                        matchColor = matchMags[filtNum] - matchMags[filtNum+1]
                        distanceArray = np.power((colorSet[filtNum] - matchColor),2)
                    matchedSEDNum = np.nanargmin(distanceArray)
                    sedMatches[currentIndex] = sedList[matchedSEDNum].name
                    magNormVal = self.calcMagNorm(matchMags, sedList[matchedSEDNum],galPhot,
                                                  redshift = catRedshifts[currentIndex],
                                                  stepSize = np.power(10, -float(magNormAcc)))
                    magNormMatches[currentIndex] = magNormVal
                    numOn += 1
                else:
                    break
            lastRedshift = redshift

        print 'Done Matching. Matched %i catalog objects to SEDs' % (len(catMags))

        return sedMatches, magNormMatches
