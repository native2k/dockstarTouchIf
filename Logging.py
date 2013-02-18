
from logging import Formatter, FileHandler, StreamHandler
from logging import debug, info, error, warning, critical
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler, SysLogHandler
import logging, sys


from types import StringTypes, IntType, ListType, TupleType
try:
    from twisted.python import log
    TWISTED_PYTHON = True
except Exception, e:
    print "Error importing twisted support - DISABLING: %s" % e
    TWISTED_PYTHON = False

import inspect, doctest, uuid, functools, re

from time import strftime, localtime

# check if interpreter supports inspect.stack
try:
    inspect.stack()
    USE_INSPECTSTACK = True
except:
    USE_INSPECTSTACK = False

# CUSTOM LOGLEVEL
INSCOUNT  = logging.DEBUG - 8
NOISY     = logging.DEBUG - 7
METHODS   = logging.DEBUG - 6
NETWORK   = logging.DEBUG - 4
SQLQUERY  = logging.DEBUG - 2
TIMING    = logging.INFO + 1

# STANDARD LOGLEVEL FROM PYTHON LIB
NOTSET    = logging.NOTSET
DEBUG     = logging.DEBUG
INFO      = logging.INFO
WARNING   = logging.WARNING
ERROR     = logging.ERROR
CRITICAL  = logging.CRITICAL

DEFAULT_LEVEL = logging.INFO

LEVELS = {'debug'    : DEBUG,
          'info'     : INFO,
          'warning'  : WARNING,
          'error'    : ERROR,
          'critical' : CRITICAL,
          'noisy'    : NOISY,
          'methods'  : METHODS,
          'network'  : NETWORK,
          'sqlquery' : SQLQUERY,
          'inscount' : INSCOUNT,
          'timing'   : TIMING,
          }




for name, value in LEVELS.items():
    logging.addLevelName(value, name.upper())

def levelToInt(level, default = INFO):
    """ handy function to convert string/int loglevel to theire int representation

    python logging only works with integer log levels, but we added our own levels
    and want to have some easy way to convert

    >>> levelToInt('warning')  == WARNING
    True

    >>> levelToInt('foo', SQLQUERY) == SQLQUERY
    True
    """
    if isinstance(level, StringTypes):
        level = LEVELS.get(level.lower(), default)
    elif not isinstance(level, IntType) or level <= 0:
        level = default
    return level

def createSessionID(length = 10):
    return "S%s" % uuid.uuid4().get_hex()[:length].upper()


class SessionStore(dict):
    """ a dict that contains logging for session handling
    >>> log = startLoggingTo('doctest', 'stdout', 'noisy')
    >>> store = SessionStore(session = '123', blub = 12234, aba = 4566, cbc = {'1': 1})
    >>> store['blub']
    12234
    >>> store.aba
    4566
    >>> store.sfsfsf
    Traceback (most recent call last):
            ....
    AttributeError: 'SessionStore' object has no attribute 'sfsfsf'

    >>> store.cbc[3] = 4
    >>> store.cbc
    {'1': 1, 3: 4}

    >>> store.info('blub')
    [INFO,store 123] blub
    """
    def __init__(self, *args, **kw):
        super(SessionStore, self).__init__(*args, **kw)
        self._log = kw.get('log') or getLogger('store')

        if kw.get('session'):
            self._log.session = kw['session']
        elif kw.get('sessionId'):
            self._log.session = kw['session']
        elif not hasattr(self._log, 'session'):
            self._log.session = createSessionID()

        self.keyAsAttributes = kw.get('keysAsAttributes', True)

    def __getattr__(self, name):
        if hasattr(self._log, name):
            return getattr(self._log, name)
        elif self.keyAsAttributes and name in self:
            return self.__getitem__(name)
        else:
            raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, name))



class WrapLogger(object):
    """ wrapper class to extend the standard python logger

    needed to make it possible for getLogger to return an standard like python
    logger with just a few improvements

    - posible to handle strings als loglevel for log, setLevel and isEnabledFor
    - contains methods for the additional loglevels like logger.info, logger.warning ...

    - If it contains an attribute session it will automtic provide its value as as
      Session-ID to the Formatter. (exp. Let your session class just inherit WrappLogger
      and after setting you sessionID to a valid value just use yourSessionClassInstance.info
      or yourSessionClassInstance.warning ... for logging

    - If you want to log a larger Block of Information you can use logBlock Method


    """

    def __init__(self, name = ''):
        self._name = name
        self._logger = logging.getLogger(name)

    def setName(self, val):
        self._name = val
        self._logger.name = val

    def __getattr__(self, name):
        if name in ['setLevel', 'isEnabledFor']:
            return functools.partial(self._wrapMethods, getattr(self._logger, name))
        elif name in ['log']:
            return functools.partial(self._log)
        elif name in LEVELS:
            #return functools.partial(self._logger.log, LEVELS[name])
            return functools.partial(self._log, LEVELS[name])
        elif hasattr(self._logger, name):
            return getattr(self._logger, name)
        #elif hasattr(self, name):
        #    return getattr(self, name)
        else:
            raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, name))

    def _wrapMethods(self, ref, level, *args, **kwargs):
        plevel = self.levelToInt(level)
        return ref(plevel, *args, **kwargs)

    def _log(self, level, *args, **kwargs):
        # add extra data if not allready there
        if 'extra' not in kwargs:
            kwargs['extra'] = {}

        if not 'classname' in kwargs['extra']:
                kwargs['extra']['classname'] = self.__class__.__name__
        if not 'method' in kwargs['extra']:
            if USE_INSPECTSTACK:
                mname = inspect.stack()[1][3]
                if mname in ['logBlock']:
                    mname = inspect.stack()[2][3]
                kwargs['extra']['method'] = mname
            else:
                kwargs['extra']['method'] = ''

        ## auto append session id
        if hasattr(self, 'session'):
            if not 'session' in kwargs['extra']:
                kwargs['extra']['session'] = self.session

        return self._logger.log(self.levelToInt(level), *args, **kwargs)


    def levelToInt(self, *args, **kwargs):
        """ converts text log level to Int value """
        return levelToInt(*args, **kwargs)

    def logBlock (self, level, data, name = '', delimLen = 50, delimStart = '+', delimEnd = '=', delimSep = '-', mode = 'header', **kwargs):
        """ log block for bigger data

            mode 'header':
                ++++++++  name +++++++++
                 ... data ...
                ========================
            mode 'full':
                +name++name++name+
                 ... data ...
                =name==name==name=
            if name is empty it will loook like
                ++++
                 ... data ...
                ====

        """
        if not self.isEnabledFor(level):
            return None

        head, foot = '', ''
        if not isinstance(data, (TupleType, ListType)):
            data = [data]

        if not name :
            head = delimStart * delimLen
            foot = delimEnd * delimLen
        else:
            nlen = len(name)
            if mode == 'full':
                elecount = int(delimLen) / (nlen + 2)
                head = ('%s%s%s' % (delimStart, name, delimStart)) * elecount
                foot = ('%s%s%s' % (delimEnd, name, delimEnd)) * elecount
            else:
                headcount = (int(delimLen) - nlen - 2) / 2
                footcount = headcount*2 + 2 + nlen
                head = '%s %s %s' % (delimStart*headcount, name, delimStart*headcount)
                foot = delimEnd * footcount

        self._log(level, head, **kwargs)
        for i, ele in enumerate(data):
            if i > 0:
                self._log(level, delimSep * delimLen, **kwargs)
            for line in ele.split('\n') :
                self._log(level, line, **kwargs)
        self._log(level, foot, **kwargs)

    def logCallbackResult(self, result, level, name = '', overrideMethod = None, call = None, **kwargs):
        """ just a fast method to log an callback result and returns the original result
            if name contains %s it used in logmessage for string replace otherwise
            logBlock is used and name is used for header

            With overrideMethod it is possible to override the method part of the log record,
            to make it better recognoizable in logfile.

            With call you can provide an function wich takes result as parameter
        """
        if self.isEnabledFor(level):
            if overrideMethod:
                if 'extra' not in kwargs:
                    kwargs['extra'] = {}
                kwargs['extra']['method'] = overrideMethod

            if call and callable(call):
                result = call(result)
            if not isinstance(result, StringTypes):
                result = str(result)

            if name and isinstance(name, StringTypes) and '%s' in name:
                msg = name % (result, )
                self._log(level, msg, **kwargs)
            else:
                self.logBlock(level, result, name, **kwargs)

        return result

Logging = SessionLogger = WrapLogger

class BufferedStream:
    """ small stream like class with small buffer,
    cause logger takes care of linebreak so this
    streams buffers the data and flushes it on linebreak
    """
    def __init__(self, ref):
        self._ref = ref
        self._buffer = []

    def write(self, text):
        if '\n' in text:  # flush data
            textl = text.split('\n')
            self._ref("".join(self._buffer + textl[:1]))
            self._buffer = textl[1:]
        else:  # just buffer data
            self._buffer.append(text)

def getLogger(name = ''):
    """ just a function to return a ready to use logger instance, can be used like the standard python version"""
    return WrapLogger(name)


def startLoggingTo(loggerName, location = None, logLevel='debug', logFormat = '[%(levelname)s,%(name)s %(session)s] %(message)s', stream = None, rotation='midnight', overrideStdIO = False):
    """ starts logging to multiple locations

    @param loggerName name of the requested logger
    @param location   Location to log to, can be a list of tuples, a list of strings or a single string
    @param logLevel   int or str representation of the min level
                      of logmessages to be shown
    @param rotation   default is to rotate the file on midnight,
                      @see logging.handlers.TimedRotatingFileHandler for
                      different values or False if no rotating is desired
    @param logFormat  overrides the log entry format
    @param overrideStdIO also reroute StdIO to this Logger (for imported lib that still use print)

    location: - if only a string - log only to this location
              - list of strings log to all provided locations
              - if tuple used instead of single location string the following
                tuple parts describes the log level threshold and logFormat for this
                location
              - if location string is            logging will go to
                               io, stdio, out                       sys.stdout
                               err, stderr                          sys.stderr
                               syslog:logserver.com:911             syslog an seveer logserver.com:911
                               syslog                               local syslog
                               /tmp/logfile.log                     to file '/tmp/logfile.log'

    """
    try:
        level = int(logLevel)
    except:
        level = levelToInt(logLevel, DEBUG)

    #logging = logging.getLogger('')
    logger = getLogger()

    logger.setLevel(level)
    logger.setName(loggerName)

    formatter = SessionFormatter(logFormat)

    # you cann supply more than one locations
    if not isinstance(location, ListType):
        location = [location]

    for loc in location:
        ## you can use a tuple to provide different loglevel or format strings for each handler
        locLevel = level
        locFormat = None
        if isinstance(loc, TupleType):
            locTo = loc[0]
            for ele in loc[1:]:
                if levelToInt(ele, -1) >= 0:
                    locLevel = levelToInt(ele)
                elif isinstance(ele, StringTypes):
                    locFormat = ele
        else:
            locTo = loc

        if locFormat:
            locFormatter = SessionFormatter(locFormat)
        else:
            locFormatter = formatter

        ## if None default to std.io
        if locTo is None:
            locTo = sys.stdout

        ## allow string representation for std streams
        streamMap = {'io': sys.stdout, 'err': sys.stderr, 'stdio': sys.stdout, 'stderr': sys.stderr, 'stdout' : sys.stdout, 'out' : sys.stdout}
        if isinstance(locTo, StringTypes) and  locTo in streamMap:
                locTo = streamMap[locTo]

        ## decide
        # string -> file, syslog
        if isinstance(locTo, StringTypes):
            if locTo.startswith('syslog'):
                if ':' in locTo:
                    address = tuple(locTo.split(':')[1:])
                    if len(address) == 1:
                        address = address[0]
                else:
                    address = ''

                if address:
                    handler = SysLogHandler(address=address) # facility = LOG_USER, socktype=socket.SOCK_DGRAM)
                else:
                    handler = SysLogHandler()
            elif rotation:
                if 'midnight' in rotation:
                    handler = TimedRotatingFileHandler(filename=locTo, when=rotation)
                else:
                    rotation = rotation.upper()
                    rotPat = re.compile('(\d+)B(\d)?')
                    if re.match('(\d+[WDHMS])+', rotation):
                        handler = TimedRotatingFileHandler(filename=locTo, when=rotation)
                    elif rotPat.match(rotation):
                        rbytes, backupc = rotPat.findall(rotation)[0]
                        backupc = int(backupc) or 0
                        handler = RotatingFileHandler(filename=locTo, maxBytes=rbytes, backupCount=backupc)
                    else:
                        FileHandler(filename=locTo)
            else:
                handler = FileHandler(filename=locTo)

        ## stream -> stream
        elif isinstance(locTo, (file, doctest._SpoofOut)):
            if overrideStdIO:
                overrideStdIO = False
            handler = StreamHandler(locTo)
        else:
            raise Exception('Not supported loc location:  %s' % locTo)

        # set maini level lower if needed
        if locLevel < level:
            logger.setLevel(locLevel)

        handler.setLevel(locLevel)
        handler.setFormatter(locFormatter)
        logger.addHandler(handler)

    if TWISTED_PYTHON:
        ## add python observer
        observer = log.PythonLoggingObserver()
        observer.start()

    ## remap stdout
    # lot of old libs log to standart out,
    # if you like to see the output .. remap it
    if overrideStdIO:
        sioLogger = getLogger("%s.stdIO" % logger.name)
        #sys.stderr = BufferedStream(sioLogger.error)
        sys.stdout = BufferedStream(sioLogger.info)

    return logger

def startLoggingToConsole(loggerName, logLevel='debug', logFormat = '[%(levelname)s,%(name)s %(session)s] %(message)s', stream = None):
    """ starts python logging facility to log to standard output
    """
    return startLoggingTo(loggerName, location = stream, logLevel = logLevel, logFormat = logFormat)

def startLoggingToFile(loggerName, filename, logLevel='debug', rotating='midnight',
                       logFormat='%(asctime)s [%(levelname)s,%(name)s %(session)s] %(message)s', overrideStdIO = False):
    """ Starts python logging facility to log into file

    @param loggerName name of the requested logger
    @param filename   name of the file to log into
    @param logLevel   int or str representation of the min level
                      of logmessages to be shown
    @param rotation   default is to rotate the file on midnight,
                      @see logging.handlers.TimedRotatingFileHandler for
                      different values or False if no rotating is desired
    @param logFormat  overrides the log entry format
    """
    return startLoggingTo(loggerName, location = filename, logLevel = logLevel, logFormat = logFormat, rotation=rotating, overrideStdIO=overrideStdIO)

class SessionFormatter(Formatter):

    def format(self, record):
        if not getattr(record, 'session', None):
            record.session =  ''
            record.sessionLS = ' %s' % record.session
            record.sessionRS = '%s ' % record.session
        else:
            record.sessionLS = ' %s' % record.session
            record.sessionRS = '%s ' % record.session

        if not getattr(record, 'classname', None):
            record.classname = ''
        if not getattr(record, 'method', None):
            record.method = record.funcName
        if not getattr(record, 'classAndmethod', None):
            if record.method and record.classname:
                record.classAndMethod = '%s::%s' % (record.classname, record.method)
            else:
                record.classAndMethod = ''

        created = localtime(record.created)
        record.date = strftime('%Y-%m-%d', created)
        record.time = strftime('%H:%M:%S', created)
        record.asctimeshort = '%s %s' % (record.date, record.time)

        #return Formatter.format(self, record)

        ## splits the record and formats every line
        msg = record.getMessage()
        res = []
        for line in msg.split("\n"):
            record.msg, record.args = line, None
            res.append(Formatter.format(self, record))
        return "\n".join(res)




if __name__ == "__main__":

    doctest.testmod()

