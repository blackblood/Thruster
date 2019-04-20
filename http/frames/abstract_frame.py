from abc import ABCMeta, abstractmethod

class AbstractFrame(object, metaclass=ABCMeta):
    @abstractmethod
    def read(self):
        pass
    
    @abstractmethod
    def write(self):
        pass