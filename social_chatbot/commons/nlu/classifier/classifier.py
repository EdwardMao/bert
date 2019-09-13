from abc import ABCMeta, abstractmethod


class BaseClassifier(object):

    def __init__(self):
        pass

    @abstractmethod
    def classify(self, query):
        pass
