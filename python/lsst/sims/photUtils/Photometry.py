"""
photUtils - 


ljones@astro.washington.edu  (and ajc@astro.washington.edu)

and now (2014 March 28): scott.f.daniel@gmail.com

Collection of utilities to aid usage of Sed and Bandpass with dictionaries.

"""

import os
import numpy
import lsst.sims.photUtils.Sed as Sed
import lsst.sims.photUtils.Bandpass as Bandpass
from lsst.sims.catalogs.measures.instance import compound

class PhotometryBase(object):
    """
    This mixin provides the basic infrastructure for photometry.
    It can read in SEDs and bandpasses, apply extinction and redshift, and, given
    an SED object it can calculate magnitudes.
    
    In order to avoid duplication of work, the bandPasses, wavelength array, and phi array
    are stored as instance variables once they are read in by self.loadBandPasses()
    
    bandPassKey is a list of the names of the bandpasses being used (e.g. 'u','g','r','i','z','y')
    
    To initiailize a different set of bandPasses, call self.loadBandPasses() with a different
    set of arguments.
    
    Once self.loadBandPasses() as been called, self.loadSeds() can be used to return an array
    of SED objects.  These objects can be passed to self.manyMagCalc_dict() which will calculate
    the magnitudes of the the SEDs, integrated over the loaded bandPasses, and return them as a 
    dict keeyed to the array of bandpass keys stored in self.bandPassKey
    """
    
    bandPassList = None
    phiArray = None
    waveLenStep = None

    def setupPhiArray_dict(self):
        """ 
        Generate 2-dimensional numpy array for Phi values associated with the bandpasses in
        self.bandPasses
  
        The results from this calculation will be stored in the instance variables
        self.phiArray and self.waveLenStep for future use by self.manyMagCalc_dict()
        """
        
        sedobj = Sed()
        self.phiArray, self.waveLenStep = sedobj.setupPhiArray(self.bandPassList)

    def loadBandPasses(self,bandPassNames, bandPassDir = None, bandPassRoot = None):
        """
        This will take the list of band passes in bandPassList and use them to set up
        self.bandPasses, self.phiArray and self.waveLenStep (which are being cached so that 
        they do not have to be loaded again unless we change which bandpasses we want)
        
        bandPassRoot contains the first part of the bandpass file name, i.e., it is assumed
        that the bandPasses are stored in files of the type
        
        $LSST_THROUGHPUTS_DEFAULT/bandPassRoot_bandPassList[i].dat
        
        if we want to load bandpasses for a telescope other than LSST, we would do so
        by altering bandPassRoot (currently no infrastructure exists for altering the directory
        in which bandpass files are stored)
        """
  
        if bandPassRoot == None:
            bandPassRoot = 'total_'
        
        self.bandPassList = []

        #A hack to get around the fact that I can't get SCons to pass through env vars.
        #path = os.getenv('LSST_THROUGHPUTS_DEFAULT_DIR')
        if bandPassDir == None:
            bandPassDir = os.path.join(os.getenv('THROUGHPUTS_DIR'),'baseline')
 
        for w in bandPassNames:   
            bandPassDummy = Bandpass()
            bandPassDummy.readThroughput(os.path.join(bandPassDir,"%s.dat" % (bandPassRoot + w)))
            self.bandPassList.append(bandPassDummy)
        
        self.phiArray = None
        self.waveLenStep = None
            
    # Handy routines for handling Sed/Bandpass routines with sets of dictionaries.
    def loadSeds(self, sedList, magNorm=15.0, resample_same=False):
        """
        Takes the list of filename sedList and returns an array of SED objects.
        
        This code will load identical SEDs twice because it is possible for
        (astronomical) objects to have the same SEDs but different magNorms
        
        @param [in] sedList is a list of file names containing Seds
        
        @param [in] magNorm is the magnitude normalization
        
        @param [in] resample_same governs whether or not to resample the Seds
        so that they are all on the same wavelength grid
        
        @param [out] sedOut is a list of Sed objects
        
        """    
        
        dataDir=os.getenv('SIMS_SED_LIBRARY_DIR')
        
        #initialize a delta function bandpass for use in applying magNorm
        imsimband = Bandpass()
        imsimband.imsimBandpass()
        
        sedOut=[]
       
        #uniqueSedDict will store all of the unique SED files that have been
        #loaded.  If an object requires an SED that has already been loaded,
        #it will just copy it from the dict.
        uniqueSedDict={}

        firstsed = True
        uniqueSedDict["None"] = Sed()
        for i in range(len(sedList)):
            sedName = sedList[i]
                     
            if sedName not in uniqueSedDict:
                sed = Sed()
                sed.readSED_flambda(os.path.join(dataDir, self.specFileMap[sedName]))

                if resample_same:
                    if firstsed:
                        wavelen_same = sed.wavelen
                        firstsed = False
                    else:
                        sed.resampleSED(wavelen_same)
                
                uniqueSedDict[sedName]=sed
        
        #now that we have loaded and copied all of the necessary SEDs,
        #we can apply magNorms
        for i in range(len(sedList)):
            
            ss = uniqueSedDict[sedList[i]]
    
            sed=Sed(wavelen=ss.wavelen,flambda=ss.flambda,fnu=ss.fnu, name=ss.name)
            
            if sedList[i] != "None":
                fNorm = sed.calcFluxNorm(magNorm[i], imsimband)
                sed.multiplyFluxNorm(fNorm)
           
            sedOut.append(sed)
        
        return sedOut
    
    def applyAvAndRedshift(self,sedList, internalAv=None, redshift=None):
        """
        Take the array of SED objects sedList and apply the arrays of extinction and redshift
        (internalAV and redshift)
        
        This method does not return anything.  It makes the necessary changes
        to the Seds in SedList in situ.
        
        @param [in] sedList is a list of Sed objects
        
        @param [in] internalAv is the Av extinction internal to the object
        
        @param [in] redshift
        
        """
        
        wavelen_sampled=[]
        
        for i in range(len(sedList)):
            if sedList[i].wavelen != None:
                if internalAv != None:
                    #setupCCMab only depends on the wavelen array
                    #because this is supposed to be the same for every
                    #SED object in sedList, it is only called once for
                    #each invocation of applyAvAndRedshift
                    if wavelen_sampled == [] or (sedList[i].wavelen!=wavelen_sampled).any():
                        a_int, b_int = sedList[i].setupCCMab()
                        wavelen_sampled=sedList[i].wavelen
                    
                    sedList[i].addCCMDust(a_int, b_int, A_v=internalAv[i])
                if redshift != None:
                    sedList[i].redshiftSED(redshift[i], dimming=True)
                    sedList[i].name = sedList[i].name + '_Z' + '%.2f' %(redshift[i])
                    sedList[i].resampleSED(wavelen_match=self.bandPassList[0].wavelen)

    def manyMagCalc_list(self, sedobj):
        """
        Return a list of magnitudes for a single Sed object.
        
        Bandpass information is taken from the instance variables self.bandPasses, self.bandPassKey,
        self.phiArray, and self.waveLenStep
        
        @param [in] sedobj is an Sed object
        
        @param [out] magList is a list of magnitudes in the bandpasses stored in self.bandPassList
        """
        # Set up the SED for using manyMagCalc - note that this CHANGES sedobj
        # Have to check that the wavelength range for sedobj matches bandpass - this is why the dictionary is passed in.
        
        magList = []
        if sedobj.wavelen != None:
            sedobj.resampleSED(wavelen_match=self.bandPassList[0].wavelen)
            
            #for some reason, moving this call to flambdaTofnu() 
            #to a point earlier in the 
            #process results in some SEDs having 'None' for fnu.
            #
            #I looked more carefully at the documentation in Sed.py
            #Any time you update flambda in any way, fnu gets set to 'None'
            #This is to prevent the two arrays from getting out synch
            #(e.g. renormalizing flambda but forgettint to renormalize fnu)
            #
            sedobj.flambdaTofnu()            
            
            magArray = sedobj.manyMagCalc(self.phiArray, self.waveLenStep)
            i = 0
            for f in self.bandPassList:
                magList.append(magArray[i])
                i = i + 1
        else:
            for f in self.bandPassList:
                magList.append(None)
                  
        return magList

    def calculatePhotometricUncertaintyFromColumn(self, nameTag, columnNames):
        """
        This method reads in a dict of column names and passes out
        the associated photometric uncertainties.  The output will be
        a dict of lists.
        
        @param [in] nameTag is the name of the column used to identify each object
        
        @param [in] columnNames is a dict associating filter names with column names,
        e.g. columnName['u'] = 'lsst_u' if the u magnitude is stored in the column
        'lsst_u'
        
        @param [out] outputDict is a dict of lists such that outputDict['u'] is a list
        of the u band photometric uncertainties for all of the objects queried
        
        """
        
        inputDict={}
        
        idNames = self.column_by_name(nameTag)
        
        magnitudes = {}
        
        for filterName in columnNames:
            magnitudes[filterName] = self.column_by_name(columnNames[filterName])
        
        outputDict = self.calculatePhotometricUncertainty(magnitudes)
        
        return outputDict
        
    def calculatePhotometricUncertainty(self, magnitudes):
        """
        This method is based on equations 3.1, 3.2 and Table 3.2
        of the LSST Science Book (version 2.0)
        
        @param [in] magnitudes will be a dict of lists such that
        magnitudes['A'] will be a list of all the magnitudes in filter A
        
        @param [out] sigOut is a dict of lists such that sigOut['A'] is
        a list of the photometric uncertainties in filter A
        """
        sigma2Sys = 0.003*0.003 #also taken from the Science Book
                         #see the paragraph between equations 3.1 and 3.2
        
        gamma = {}
        m5 = {}
        
        gamma['u'] = 0.037
        gamma['g'] = 0.038
        gamma['r'] = 0.039
        gamma['i'] = 0.039
        gamma['z'] = 0.040
        gamma['y'] = 0.040
        
        m5['u'] = 23.9
        m5['g'] = 25.0
        m5['r'] = 24.7
        m5['i'] = 24.0
        m5['z'] = 23.3
        m5['y'] = 22.1
        
        sigOut={}
        
        for filterName in magnitudes:
            
            subList = []
            
            for i in range(len(magnitudes[filterName])):
                mm = magnitudes[filterName][i]
               
                if mm != None and mm>-990.0:
                    xx=10**(0.4*(mm - m5[filterName]))
                    ss = (0.04 - gamma[filterName])*xx + \
                         gamma[filterName]*xx*xx
                
                    sigmaSquared = ss + sigma2Sys
                
                    subList.append(numpy.sqrt(sigmaSquared))
                
                else:
                    subList.append(None)
                
            sigOut[filterName] = subList
        
        return sigOut

class PhotometryGalaxies(PhotometryBase):
    """
    This mixin provides the code necessary for calculating the component magnitudes associated with
    galaxies.  It assumes that we want LSST filters.
    """
    
    def calculate_component_magnitudes(self,objectNames, componentNames, \
                                       magNorm = 15.0, internalAv = None, redshift = None):
        
        """
        Calculate the magnitudes for different components (disk, bulge, agn, etc) of galaxies.
        This method is designed to be used such that you feed it all of the disk Seds from your data
        base and it returns the associated magnitudes.  Then you feed it all of the bulge Seds, etc.
        
        @param [in] objectNames is the name of the galaxies (the whole galaxies)
        
        @param [in] componentNames gives the name of the SED filenames
    
        @param [in] magNorm is the normalizing magnitude
        
        @param [in] internalAv is the internal Av extinction
        
        @param [in] redshift is pretty self-explanatory
        
        @param [out] componentMags is a dict of lists such that
        magnitude["objectname"][i] will return the magnitude in the ith
        for the associated component Sed
        
        """
        
        componentMags = {}
        
        if componentNames != []:
            componentSed = self.loadSeds(componentNames, magNorm = magNorm)
            self.applyAvAndRedshift(componentSed, internalAv = internalAv, redshift = redshift)
            
            for i in range(len(objectNames)):
                subList = self.manyMagCalc_list(componentSed[i])
                componentMags[objectNames[i]] = subList
        
        else:
            subList=[]
            for b in self.bandPassList:
                subList.append(None)
            for i in range(len(objectNames)):
                componentMags[objectNames[i]]=subList
    
        return componentMags
    
    def sum_magnitudes(self, disk = None, bulge = None, agn = None):
        """
        Sum the component magnitudes of a galaxy and return the answer
        
        @param [in] disk is the disk magnitude
        
        @param [in] bulge is the bulge magnitude
        
        @param [in] agn is the agn magnitude
        
        @param [out] outMag is the total magnitude of the galaxy
        """
        
        mm_o = 22.
        
        nn=0.0
        if disk is not None and (not numpy.isnan(disk)):
            nn+=numpy.power(10, (disk - mm_o)/-2.5)
                
        if bulge is not None and (not numpy.isnan(bulge)):
            nn+=numpy.power(10, (bulge - mm_o)/-2.5)
            
        if agn is not None and (not numpy.isnan(agn)):
            nn+=numpy.power(10, (agn - mm_o)/-2.5)
                
        if nn>0.0:
            outMag = -2.5*numpy.log10(nn) + mm_o
        else:
            outMag = None
        
        return outMag
    
    def calculate_magnitudes(self, idNames):
        """
        Take the array of bandpass keys bandPassList and the array of galaxy
        names idNames ane return a dict of dicts of dicts of magnitudes
        
        the first level key is galid (the name of the galaxy)
        
        the second level key is "total", "bulge", "disk", or "agn"
        
        the third level key is bandPassList
        
        We need to index the galaxies by some unique identifier, such as galid
        because it is possible for galaxies to have the same sed filenames but 
        different normalizations
        
        @param [in] bandPassList is a list of bandPass names (e.g. 'u', 'g', 'r', 'i', 'z', 'y')
        self.loadBandpasses will handle turning these into proper file names
        
        @param [in] idNames is a list of names uniquely identifying the objects whose magnitudes
        are being calculated
        
        @param [in] bandPassRoot is the root of the filename of bandpasses (i.e. bandpasses are
        stored in files named bandPassRoot_u.dat etc.).  If None, defaults to
        'total_'
        
        @param [out] masterDict is a dict of magnitudes such that
        masterDict['AAA']['BBB']['x'] is the magnitude in filter x of component BBB of galaxy AAA
        
        
        """

        diskNames=self.column_by_name('sedFilenameDisk')
        bulgeNames=self.column_by_name('sedFilenameBulge')
        agnNames=self.column_by_name('sedFilenameAgn')

        diskmn = self.column_by_name('magNormDisk')
        bulgemn = self.column_by_name('magNormBulge')
        agnmn = self.column_by_name('magNormAgn')
        
        bulgeAv = self.column_by_name('internalAvBulge')
        diskAv = self.column_by_name('internalAvDisk')

        redshift = self.column_by_name('redshift')
         
        diskMags = self.calculate_component_magnitudes(idNames,diskNames,magNorm = diskmn, \
                        internalAv = diskAv, redshift = redshift)
                        
        bulgeMags = self.calculate_component_magnitudes(idNames,bulgeNames,magNorm = bulgemn, \
                        internalAv = bulgeAv, redshift = redshift)
                        
        agnMags = self.calculate_component_magnitudes(idNames,agnNames,magNorm = agnmn, \
                        redshift = redshift)
        
        total_mags = []
        masterDict = {}

        for i in range(len(idNames)):
            total_mags=[]
            j=0
            for ff in self.bandPassList:
                total_mags.append(self.sum_magnitudes(disk = diskMags[idNames[i]][j],
                                bulge = bulgeMags[idNames[i]][j], agn = agnMags[idNames[i]][j]))
                
                j += 1
                
            subDict={}
            subDict["total"] = total_mags
            subDict["bulge"] = bulgeMags[idNames[i]]
            subDict["disk"] = diskMags[idNames[i]]
            subDict["agn"] = agnMags[idNames[i]]
            
            masterDict[idNames[i]] = subDict


        return masterDict
     

    def meta_magnitudes_getter(self, idNames):
        """
        This method will return the magnitudes for arbitrary galaxy bandpasses
        
        @param [in] idNames is a list of object IDs
        
        @param [in] bandPassList is a list of bandpass names (e.g. 'u', 'g', 'r', 'i', etc)
        
        @param [in] bandPassRoot is the root of the bandpass file names (i.e. bandpasses
        are stored in files with names bandPassRoot_u.dat etc).  If None, default to
        'total_'
        """

        magDict=self.calculate_magnitudes(idNames)
        
        firstRowTotal = []
        firstRowDisk = []
        firstRowBulge = []
        firstRowAgn = []
        
        failure = -999.0
        for name in idNames:
            
            firstRowTotal.append(magDict[name]["total"][0])
            
            if magDict[name]["bulge"]:
                firstRowBulge.append(magDict[name]["bulge"][0])
            else:
                firstRowBulge.append(failure)
            
            if magDict[name]["disk"]:
                firstRowDisk.append(magDict[name]["disk"][0])
            else:
                firstRowDisk.append(failure)
            
            
            if magDict[name]["agn"]:
                firstRowAgn.append(magDict[name]["agn"][0])
            else:
                firstRowAgn.append(failure)
        
        
        outputTotal = numpy.array(firstRowTotal)
        outputBulge = numpy.array(firstRowBulge)
        outputDisk = numpy.array(firstRowDisk)
        outputAgn = numpy.array(firstRowAgn)
        
        i = 1
        while i<len(self.bandPassList):
            rowTotal = []
            rowDisk = []
            rowBulge = []
            rowAgn = []
            
            for name in idNames:
                rowTotal.append(magDict[name]["total"][i])
            
                if magDict[name]["bulge"]:
                    rowBulge.append(magDict[name]["bulge"][i])
                else:
                    rowBulge.append(failure)
                
                if magDict[name]["disk"]:
                    rowDisk.append(magDict[name]["disk"][i])
                else:
                    rowDisk.append(failure)
                
                if magDict[name]["agn"]:
                    rowAgn.append(magDict[name]["agn"][i])
                else:
                    rowAgn.append(failure)
                
            outputTotal = numpy.vstack([outputTotal,rowTotal])
            outputBulge = numpy.vstack([outputBulge,rowBulge])
            outputDisk = numpy.vstack([outputDisk,rowDisk])
            outputAgn = numpy.vstack([outputAgn,rowAgn])
        
            i += 1
        
        
        outputTotal = numpy.vstack([outputTotal,outputBulge])
        outputTotal = numpy.vstack([outputTotal,outputDisk])
        outputTotal = numpy.vstack([outputTotal,outputAgn])
        
        return outputTotal

    
    
    
    @compound('sigma_uRecalc','sigma_gRecalc','sigma_rRecalc',
              'sigma_iRecalc','sigma_zRecalc','sigma_yRecalc',
              'sigma_uBulge','sigma_gBulge','sigma_rBulge',
              'sigma_iBulge','sigma_zBulge','sigma_yBulge',
              'sigma_uDisk','sigma_gDisk','sigma_rDisk',
              'sigma_iDisk','sigma_zDisk','sigma_yDisk',
              'sigma_uAgn','sigma_gAgn','sigma_rAgn',
              'sigma_iAgn','sigma_zAgn','sigma_yAgn')
    def get_photometric_uncertainties(self):
        """
        Getter for photometric uncertainties associated with galaxies
        """
        
        columnNames = {}
        columnNames['u'] = 'uRecalc'
        columnNames['g'] = 'gRecalc'
        columnNames['r'] = 'rRecalc'
        columnNames['i'] = 'iRecalc'
        columnNames['z'] = 'zRecalc'
        columnNames['y'] = 'yRecalc'
        
        totalDict = self.calculatePhotometricUncertaintyFromColumn('galid',columnNames)
        
        columnNames = {}
        columnNames['u'] = 'uDisk'
        columnNames['g'] = 'gDisk'
        columnNames['r'] = 'rDisk'
        columnNames['i'] = 'iDisk'
        columnNames['z'] = 'zDisk'
        columnNames['y'] = 'yDisk'
        
        diskDict = self.calculatePhotometricUncertaintyFromColumn('galid',columnNames)
        
        columnNames = {}
        columnNames['u'] = 'uBulge'
        columnNames['g'] = 'gBulge'
        columnNames['r'] = 'rBulge'
        columnNames['i'] = 'iBulge'
        columnNames['z'] = 'zBulge'
        columnNames['y'] = 'yBulge'
        
        bulgeDict = self.calculatePhotometricUncertaintyFromColumn('galid',columnNames)
        
        columnNames = {}
        columnNames['u'] = 'uAgn'
        columnNames['g'] = 'gAgn'
        columnNames['r'] = 'rAgn'
        columnNames['i'] = 'iAgn'
        columnNames['z'] = 'zAgn'
        columnNames['y'] = 'yAgn'
        
        agnDict = self.calculatePhotometricUncertaintyFromColumn('galid',columnNames)
        
        return numpy.array([totalDict['u'],totalDict['g'],totalDict['r'],
                            totalDict['i'],totalDict['z'],totalDict['y'],
                            bulgeDict['u'],bulgeDict['g'],bulgeDict['r'],
                            bulgeDict['i'],bulgeDict['z'],bulgeDict['y'],
                            diskDict['u'],diskDict['g'],diskDict['r'],
                            diskDict['i'],diskDict['z'],diskDict['y'],
                            agnDict['u'],agnDict['g'],agnDict['r'],
                            agnDict['i'],agnDict['z'],agnDict['y']])
        
    @compound('uRecalc', 'gRecalc', 'rRecalc', 'iRecalc', 'zRecalc', 'yRecalc',
              'uBulge', 'gBulge', 'rBulge', 'iBulge', 'zBulge', 'yBulge',
              'uDisk', 'gDisk', 'rDisk', 'iDisk', 'zDisk', 'yDisk',
              'uAgn', 'gAgn', 'rAgn', 'iAgn', 'zAgn', 'yAgn')
    def get_all_mags(self):
        """
        Getter for LSST galaxy magnitudes
        
        """
        idNames = self.column_by_name('galid')
        bandPassNames = ['u','g','r','i','z','y']
        
        if self.bandPassList is None or self.phiArray is None:
            self.loadBandPasses(bandPassNames)
            self.setupPhiArray_dict()
         
        return self.meta_magnitudes_getter(idNames)
       
        

class PhotometryStars(PhotometryBase):
    """
    This mixin provides the infrastructure for doing photometry on stars
    
    It assumes that we want LSST filters.
    """
                         
    def calculate_magnitudes(self, idNames):
        """
        Take the array of bandpass keys bandPassList and the array of
        star names idNames and return a dict of dicts of magnitudes
        
        The first level key will be the name of the star (idName)
        
        The second level key will be the name of the filter (bandPassList)
        
        As with galaxies, it is important that we identify stars by a unique
        identifier, rather than their sedFilename, because different stars
        can have identical SEDs but different magnitudes.
        
        
        @param [in] bandPassList is a list of filter names (e.g. 'u', 'g', 'r', 'i', 'z', 'y')
        
        @param [in] idNames is a list of names uniquely identifying the objects being considered
        
        @param [in] bandPassRoot is the root of the filename for bandpasses (i.e. bandpasses
        are stored in files named bandPassRoot_u.dat etc.).  If 'None' defaults to
        'total_'
        
        @param [out] magDict is a dict such that
        magDict['AAA']['x'] is the magnitude in filter x of object AAA
        
        """

        sedNames = self.column_by_name('sedFilename')
        magNorm = self.column_by_name('magNorm')
        sedList = self.loadSeds(sedNames,magNorm = magNorm)
        
        magDict = {}
        for i in range(len(idNames)):
            name = idNames[i]
            subList = self.manyMagCalc_list(sedList[i])
            magDict[name] = subList
        
        return magDict

    
    def meta_magnitudes_getter(self, idNames):
        """
        This method does most of the work for stellar magnitude getters
        
        @param [in] idNames is a list of object names
        
        @param [in] bandPassList is a list of bandpass names ('u', 'g', 'r', 'i,', etc.)
        
        @param [in] bandPassRoot is the root of bandpass filenames (i.e. bandpasses are
        stored in files named bandPassRoot_u.dat etc.).  If None defaults to 'total_'
        
        @param [out] output is a 2d numpy array in which the rows are the bandpasses
        from bandPassList and the columns are the objects from idNames
        
        """

        magDict = self.calculate_magnitudes(idNames)
        
        firstRow = []
        for name in idNames:
            firstRow.append(magDict[name][0])
        
        output = numpy.array(firstRow)
        
        i = 1
        while i<len(self.bandPassList):
            row = []
            for name in idNames:
                row.append(magDict[name][i])
            
            i += 1
            
            output=numpy.vstack([output,row])
        
        return output
    
    @compound('sigma_lsst_u','sigma_lsst_g','sigma_lsst_r','sigma_lsst_i',
              'sigma_lsst_z','sigma_lsst_y')
    def get_photometric_uncertainties(self):
        """
        Getter for photometric uncertainties associated with stellar
        magnitudes
        """
    
        columnNames = {}
        columnNames['u'] = 'lsst_u'
        columnNames['g'] = 'lsst_g'
        columnNames['r'] = 'lsst_r'
        columnNames['i'] = 'lsst_i'
        columnNames['z'] = 'lsst_z'
        columnNames['y'] = 'lsst_y'
        
        outputDict = self.calculatePhotometricUncertaintyFromColumn('id',columnNames)
 

        return numpy.array([outputDict['u'],outputDict['g'],outputDict['r'],
                            outputDict['i'],outputDict['z'],outputDict['y']])


    @compound('lsst_u','lsst_g','lsst_r','lsst_i','lsst_z','lsst_y')
    def get_magnitudes(self):
        """
        getter for LSST stellar magnitudes
        
        bandPassRoot is the root of the names of the files in which
        the bandpasses are stored
        """
        idNames = self.column_by_name('id')
        bandPassNames = ['u','g','r','i','z','y']
        
        if self.bandPassList is None or self.phiArray is None:
            self.loadBandPasses(bandPassNames)
            self.setupPhiArray_dict()
            
        return self.meta_magnitudes_getter(idNames)
   
