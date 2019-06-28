from abc import ABCMeta, abstractmethod


class AbstractFrame(object, metaclass=ABCMeta):
    @abstractmethod
    def read(self):
        pass

    @abstractmethod
    def write(self):
        pass

    @abstractmethod
    def read_header(self):
        pass
    
    @abstractmethod
    def read_body(self):
        pass
    
    # @abstractmethod
    # def write_header(self):
    #     pass
    
    # @abstractmethod
    # def write_body(self):
    #     pass