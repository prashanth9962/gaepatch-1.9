__author__ = 'prashanth'
import datetime
import socket
import platform
import sys
import os
from boto.s3.key import Key
DIR_PATH = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
sys.path = sys.path+[os.path.join(DIR_PATH, 'lib', 'yaml', 'lib')]
#print "------"
#print DIR_PATH
#print "------"
#print sys.path
#from flow.exception.error import Rollbackerror , Googlesdkerror

import urllib,tempfile, httplib, urllib2
import logging
import pickle
#from flow.util.AWSUtil import s3conn
import glob
from appcfg import deploy
from os import listdir
from os.path import isfile, join
#from orangescape.model.server.util.ziputil import InMemoryZip
#import appconfig as config
#basepath = os.path.dirname(config.__file__)
basepath="/home/prashanth/IdeaProjects/HelloWorld"

finalpackagedict = None
usrargs = ['update',basepath,'--skip_sdk_update_check', 'appdir','']

def execappcfg(args):
        global usrargs
        usrargs = args
        deploy(__file__,globals())


def scan_dir(path, files, filters=None):
    for currentFile in glob.glob(os.path.join(path, '*') ):
        if os.path.isdir(currentFile):
            scan_dir(currentFile, files, filters)
        elif not filters or '.'+currentFile.split('.')[-1] not in filters:
            filePath = currentFile.replace(basepath+os.path.sep, '') if basepath else currentFile
            f = open(currentFile, 'r')
            files[filePath.replace("\\","/")]=f.read()


global files
libDict = {}
scan_dir(basepath, libDict, ['.pyc'])
files = libDict
execappcfg(usrargs)