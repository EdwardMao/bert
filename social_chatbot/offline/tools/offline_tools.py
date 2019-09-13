from abc import ABCMeta, abstractmethod


class OfflineTools(object):

    def __init__(self):
        pass

    @abstractmethod
    def execute(self):
        pass
