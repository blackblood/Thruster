from abc import ABCMeta, abstractmethod

class AbstractFrame(object):
    __metaclass__ = ABCMeta
    
    @abstractmethod
    def read():
        pass
    
    @abstractmethod
    def write():
        pass