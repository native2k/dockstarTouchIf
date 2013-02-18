#!/usr/bin/python

import time, Tkinter, os, sys
from imageshow import ShowImageApp
from mpdshow import MpdControl, MpdStatus
from pprint import pformat, pprint
import Logging
import configobj
#from optparse import OptionParser

CFG = 'touchIF.conf'
NAME = 'TouchIF'
VERSION = '1.0.0'

SIZE = 800,600

PICTURE_WAIT = 1000*60*15
PICTURE_DIRS = ["/home/sven/python/Thailand2010",
    "/home/sven/python/DD_grillabend",
    "/home/sven/python/Gozo07",
    ]

PICTURE_WAIT = 1000*1
PICTURE_DIRS = ['./pics']


class MainApp(Tkinter.Frame):


    def __init__(self, master=None, config=None, logger = None):
        Tkinter.Frame.__init__(self, master)
        self.pack()
        self.root = master
        
        self._config = config or {}
        self.log = logger or Logging.getLogger(self.__class__.__name__)
        if self.log.isEnabledFor('debug'):
            self.log.logBlock('debug', pformat(self._config))


        self.showImage()
        #self.showMpd()

    def showImage(self):
        self.log.debug('---> showImage called')
        self.mpdStatus = MpdStatus(self._config, logger = self.log)
        self.imageFrame = ShowImageApp(self, config = self._config, onQuit = self.quitImage, statusFunc = self.mpdStatus.printStatus)
        #self.root.protocol("WM_DELETE_WINDOW", self.quitImage)
    
    def quitImage(self, event = None):
        self.log.debug('---> quitImage called')
        self.imageFrame.destroy()
        self.mpdStatus.destroy()
        self.imageFrame = None
        self.mpdStatus = None
        self.showMpd()
        
    def showMpd(self):
        self.log.debug('---> showMpd called')
        self.mpdFrame =  MpdControl (self, config = self._config, onQuit = self.quitMpd)
        #self.mpdFrame.protocol("WM_DELETE_WINDOW", self.quitMpd)
         
    def quitMpd(self, event = None):
        self.log.debug('---> quitMpd called')
        self.mpdFrame.destroy()
        self.mpdFrame = None
        self.showImage()
        #self.after(1000, )
        

    
if __name__ == "__main__":

    # usage = "usage %prog [options]"
    # parser = OptionParser(usage=usage, version='%prog ' + VERSION)
    # parser.add_option("-c", "--config", dest='configfile', default=CFG, help="configuration file", metavar="CONFIG")
    # parser.add_option("-d", "--debug", dest='debug', default=False, help="enables stdout")
    # (options, args) = parser.parse_args()

    #config = configobj.ConfigObj(ioptions.configfile)
    config = configobj.ConfigObj(CFG)
    if not config:
        print "could not find CFG %s" % CFG
        sys.exit()

    L = Logging.startLoggingTo('TouchIF', config['main'].get('logfile', 'stdio'),
                           config['main'].get('loglevel', 'info'))
    L.info('starting %s (ver %s)' % (NAME, VERSION))

    if config['image'].get('path'):
        config['image']['dirs'] = [path for path, dirs, files in os.walk(config['image']['path'])
                                   if '/.' not in path]

    root = Tkinter.Tk()
    root.overrideredirect(True)
    root.config(bg="grey")
    #root.bind("<Button>", button_click_exit_mainloop)
    config['main']['sizepos'] = tuple([int(i) for i in config['main'].get('size', SIZE) + config['main'].get('pos', (0,0))])
    print pformat(config)
    root.geometry('%dx%d+%d+%d' % config['main']['sizepos'])

    app = MainApp(master=root, config = config, logger = L)
    app.mainloop()
    root.destroy()

