from abc import ABCMeta, abstractmethod

class AbstractFrame(object):
    __metaclass__ = ABCMeta
    
    @abstractmethod
    def read(self):
        pass
    
    @abstractmethod
    def write(self):
        pass