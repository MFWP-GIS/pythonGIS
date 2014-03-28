#-------------------------------------------------------------------------------
# Name:        gisMetadata
# Purpose:     A module associate with managing Argis 1.0 format metadata

# Created By:  Bill Daigle 28Mar2014
#-------------------------------------------------------------------------------

import datetime
import arcpy
import os
import xml.etree.ElementTree as et
import shutil
import tempfile


def backupMetadataToXml(datasetPath,xmlBackupPath = None):
    '''Adds a process step to an existing metadata element tree

        Inputs:
            datasetPath(required): path to the dataset with metadata
            xmlBackupPath(optional): output file path.  If not provided, a temporary file will be created
        Outputs: the path to the backup file
    '''

    filepath = _createDummyXMLFile()
    arcpy.MetadataImporter_conversion(datasetPath, filepath)
    if xmlBackupPath != None:
        shutil.copy2(filepath,xmlBackupPath)
        return xmlBackupPath
    else:
        return filepath

def restoreMetadataFromBackup(xmlBackupPath,datasetPath):
    '''puts metadata back into its original state

        Inputs:
            xmlBackupPath(required): path to the xml file
            datasetPath(required): path to the dataset to be restored
        Outputs: none
    '''
    arcpy.MetadataImporter_conversion(xmlBackupPath,datasetPath)

def upgradeMetadataFormatToArcgis1_0(datasetPath, maintainFgdcTitle=True):
    '''updates an item's metadata to ArcGIC 1.0 format

        Inputs:
            datasetPath(required): path to the dataset to be restored
        Outputs: none
    '''
    #fetch the current metadata
    mdo = export_to_ElementTree(datasetPath)

    #fetch the FGDC title of the dataset if necessary
    if maintainFgdcTitle == True:
        fgdcTitle = getTagText(mdo,'idinfo/citation/citeinfo/title')
        if fgdcTitle == None:
             maintainFgdcTitle = False


    #upgrade the metadata if it hasn't been done yet
    if (getTagText(mdo,'Esri/ArcGISFormat') != '1.0'):

        arcpy.UpgradeMetadata_conversion(datasetPath, 'FGDC_TO_ARCGIS')

        #fetch the metadata again so the FGDC tags can be deleted
        mdo = export_to_ElementTree(datasetPath)

    #delete the FGDC tags
    root = mdo.getroot()
    #list of all tags except 'eainfo' and 'spdoinfo' since ArcGIS 1.0 uses these
    fgdcTags = ['idinfo','dataqual','spref','distinfo','metainfo','citeinfo','timeinfo','cntinfo']
    for fgdcTag in fgdcTags:
        for child in root:
            if child.tag == fgdcTag:
                root.remove(child)

    #import the updated element tree
    import_from_ElementTree(mdo,datasetPath)

    #set the synchronization attributes
    arcpy.SynchronizeMetadata_conversion(datasetPath,'ALWAYS')

    #reset the sync type for the title tag
    syncedMdo = export_to_ElementTree(datasetPath)
    titleTag = syncedMdo.find('dataIdInfo/idCitation/resTitle')
    titleTag.attrib['Sync'] = 'FALSE'

    #update the title tag if necessary
    if maintainFgdcTitle == True:

        updateTagText(syncedMdo,'dataIdInfo/idCitation/resTitle',fgdcTitle)

    #import the updated element tree
    import_from_ElementTree(syncedMdo,datasetPath)


def getTagText(elementTree,tagPath):
    '''Fetches the text from an element tree tag

        Inputs:
            elementTree(required): element tree object
            tagPath(required): path to the tag in the metadata (i.e 'idinfo/citation/citeinfo/origin')
        Outputs: modified element tree
    '''
    try:
        tag = elementTree.find(tagPath)
        tagText = tag.text
    except:
        tagText = None
    return tagText

def updateTagText(elementTree,tagPath,newText):
    '''Updates the text from an element tree tag

        Inputs:
            elementTree(required): element tree object
            tagPath(required): path to the tag in the metadata (i.e 'idinfo/citation/citeinfo/origin')
            newText(required): new text (i.e. 'Montana Fish Wildlife and Parks')
        Outputs: modified element tree
    '''
    try:
        tag = elementTree.find(tagPath)
        tag.text = newText
    except:
        print 'could not update tag'
        pass
    return elementTree

def export_to_ElementTree(dataset):
    '''Creates and returns an ElementTree object from the specified dataset.
       Dataset can be an ArcGIS item or a standalone xml file

        Inputs:
            dataset(required): path to the dataset or xml file

        Outputs: ElementTree object
    '''
    xmlfile = _createDummyXMLFile()
    arcpy.MetadataImporter_conversion(dataset, xmlfile)
    elementTree = et.ElementTree()
    elementTree.parse(xmlfile)
    os.remove(xmlfile)
    return elementTree

def import_from_ElementTree(elementTree,dataset):
    '''Updates an ArcGIS item (or standalone xml) file using an element tree object

        Inputs:
            elementTree(required): an element tree object representing the new metadata
            dataset(required): path to the dataset or xml file

        Outputs: None
    '''
    fd, filepath = tempfile.mkstemp(".xml", text=True)
    with os.fdopen(fd, "w") as f:
        f.close()
    elementTree.write(filepath)
    arcpy.MetadataImporter_conversion(filepath, dataset)


def _createDummyXMLFile():
    tempdir = tempfile.gettempdir()
    fd, filepath = tempfile.mkstemp(".xml", text=True)
    with os.fdopen(fd, "w") as f:
        f.write("<metadata />")
        f.close()
    return filepath


