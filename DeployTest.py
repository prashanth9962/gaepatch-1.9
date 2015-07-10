__author__ = 'prashanth'
import datetime
import socket
import platform
import sys
import os
from boto.s3.key import Key
DIR_PATH = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
sys.path = sys.path+[os.path.join(DIR_PATH, 'lib', 'yaml', 'lib')]
print "------"
print DIR_PATH
print "------"
print sys.path
#from flow.exception.error import Rollbackerror , Googlesdkerror

import urllib,tempfile, httplib, urllib2
import logging
import pickle
#from flow.util.AWSUtil import s3conn
import glob
from appcfg import deploy
import zipfile
import StringIO
#from orangescape.model.server.util.ziputil import InMemoryZip
#import appconfig as config
#basepath = os.path.dirname(config.__file__)
basepath="/home/prashanth/localSetup/kissflow/flowstudio/"

finalpackagedict = None
usrargs = [basepath,'update','--skip_sdk_update_check', 'appdir']


def scan_dir(path, files, filters=None):
    for currentFile in glob.glob(os.path.join(path, '*') ):
        if os.path.isdir(currentFile):
            scan_dir(currentFile, files, filters)
        elif not filters or '.'+currentFile.split('.')[-1] not in filters:
            filePath = currentFile.replace(basepath+os.path.sep, '') if basepath else currentFile
            f = open(currentFile, 'r')
            files[filePath.replace("\\","/")]=f.read()

class GAEDeployer:
    def get_pkg_local(self, buildNo, pkgName):
        filename = pkgName+str(buildNo)+'.zip'
        if os.path.exists(os.path.join(basepath, filename)):
            logging.info('Getting pkg from local....')
            f = open(os.path.join(basepath, filename), 'rb')
            zip_File = zipfile.ZipFile(f,"r")

            zipcontentobject = InMemoryZip()
            dict = zipcontentobject.ziptodict(zip_File)
            return dict
        return self.get_pkg(buildNo, pkgName)

    def get_pkg(self, buildNo ,pkgName):
        logging.info('Getting package %s from S3 for build %s'%(pkgName, buildNo))
        package_bucket = s3conn.get_bucket('os-flow-builds')
        filename = pkgName+str(buildNo)+'.zip'
        keystrg = str(buildNo)+'/'+'patched files/'+filename
        key = package_bucket.get_key(keystrg)
        if key is None:
            keystrg = str(buildNo)+'/' + filename
            key = package_bucket.get_key(keystrg)
        packagestringcontent = StringIO.StringIO(key.get_contents_as_string())
        zip_File = zipfile.ZipFile(packagestringcontent,"r")
        zipcontentobject = InMemoryZip()
        dict = zipcontentobject.ziptodict(zip_File)
        return dict

    def modifyYaml(self, appName,yamlText):
        oldText = yamlText[0:yamlText.find('\n')]
        yamlText = yamlText.replace(oldText,'application: ' + appName)
        return yamlText

    def enable_gae_warmup(self, yamlText):
        if '\nhandlers:\r\n' in yamlText:
            yamlText = yamlText.replace('\nhandlers:\r\n', '\ninbound_services:\n- warmup\n\nhandlers:')
        elif '\nhandlers:\n' in yamlText:
            yamlText = yamlText.replace('\nhandlers:\n', '\ninbound_services:\n- warmup\n\nhandlers:')
        return yamlText

    def upload_to_gae(self, args):
        startTime = datetime.datetime.now()
        logging.info('Start Time === %s'%startTime)

        buildNo = args["buildNo"]
        appName = args["appName"]
        appData = args['packagedata']
        folder = args['folder']
#        gaeruntimedict = self.get_pkg(buildNo, 'gae-runtime-1.')
        flowruntimedict = self.get_pkg(buildNo, 'os-flow-runtime-1.')

        import appconfig as config
        from flow.services.Deploy import scan_dir
        #list of libraries to be copied to runtime
        libList = ['sqlalchemy', 'migrate', 'apiclient', 'googleapiclient', 'atom', 'gdata', 'gflags', 'httplib2',
                   'oauth2client', 'pyasn1', 'pyasn1_modules', 'rsa', 'uritemplate', 'simplejson', 'bugsnag']
        for libName in libList:
            libDict = {}
            libPath = os.path.join(os.path.dirname(config.__file__), libName)
            scan_dir(libPath, libDict, ['.pyc'])
            flowruntimedict.update(libDict)

        flowruntimedict['app.yaml'] = self.modifyYaml(appName,flowruntimedict['app.yaml'])
        if args.get('WarmUp'):
            flowruntimedict['app.yaml'] = self.enable_gae_warmup(flowruntimedict['app.yaml'])
#        gaeruntimedict.update(flowruntimedict)
        flowruntimedict.update(appData)
        finalpackagedict = {}
        global files
        files = flowruntimedict
        import appconfig as config
        basepath = os.path.dirname(config.__file__)

        args = [basepath, 'update','--skip_sdk_update_check' , 'appdir']

        self.safedeploy(args)

        if not folder:
            global usrargs
            args = [basepath, '--skip_sdk_update_check', 'backends', 'appdir', 'update', 'batch']
            self.safedeploy(args)
        """ Schema sync code for the runtime appsppot """
        logging.info('Deploy complete sucessfully , Getting to Schemasync')
#        self.schemaSync(appId, appName, userId, folder, folder)



    def safedeploy(self, args, attempt=5):
        if attempt > 0:
            try:
                self.execappcfg(args)
            except Rollbackerror , e:
                logging.info('Requesting attempt for rollback for :%s'%(5-attempt+1))
                args[args.index('update')]='rollback'
                self.execappcfg(args)
                args[args.index('rollback')]='update'
                self.safedeploy(args,attempt-1)
            except urllib2.URLError:
                logging.info('Network got jammed , retring for :%s time'%(5-attempt+1))
                self.safedeploy(args,attempt-1)
            except Googlesdkerror , e:
                logging.error(e.__str__())
                raise

    def execappcfg(self,args):
        global usrargs
        usrargs = args
        deploy(__file__,globals())

a = GAEDeployer()
a.execappcfg(usrargs)