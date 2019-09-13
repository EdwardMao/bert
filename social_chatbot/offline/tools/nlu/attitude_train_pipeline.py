import codecs
import globals
import json
import logging
import os
import pickle
import re
import sys

from commons.nlu.language_processor import LanguageProcessor
from commons.utils import space_tokenizer
from configures import NLUConfigure
from offline.tools.offline_tools import OfflineTools
from sklearn.feature_extraction.text import CountVectorizer
from sklearn import svm


class AttitudeClassifierPipeline(OfflineTools):

    def __init__(self, local_configure):

        super().__init__()
        self.exe_type = local_configure["exe_type"]
        self.data_root = local_configure["data_root"]
        self.yes_no_data_file = local_configure["data_root"] + "yes_no_data.tsv"
        self.like_dislike_data_file = local_configure["data_root"] + "like_dislike_data.tsv"
        self.language_processor = globals.nlp_processor
        self.non_char = re.compile("([^\u4E00-\u9FD5a-zA-Z0-9])")
        pass

    def execute(self):
        self.train_yes_no_classifier()
        self.train_like_unlike_classifier()
        pass

    def train_yes_no_classifier(self):

        sys.stdout.write("Start Training YESNO Classifier!\n")
        lines = codecs.open(self.yes_no_data_file, 'r', 'utf-8').read().splitlines()
        X_list = []
        Y_list = []
        for line in lines:
            elems = line.split("\t")
            assert(len(elems) == 2)
            update_data = self.non_char.sub("", elems[0].lower())
            segmented_sentence = " ".join(self.language_processor.segment_chinese_sentence_without_dictionary(update_data))
            X_list.append(segmented_sentence)
            Y_list.append(int(elems[1]))

        vectorizer = CountVectorizer(ngram_range=(1, 3), analyzer="word", tokenizer=space_tokenizer)
        X_list = vectorizer.fit_transform(X_list)

        lin_clf = svm.LinearSVC()
        lin_clf.fit(X_list, Y_list)

        model_file = self.data_root + "/yes_no_model.pickle"
        f = open(model_file, 'wb')
        pickle.dump([vectorizer, lin_clf], f)
        f.close()

    def train_like_unlike_classifier(self):

        sys.stdout.write("Start Training LIKE_DISLIKE Classifier!\n")
        lines = codecs.open(self.like_dislike_data_file, 'r', 'utf-8').read().splitlines()
        x_list = []
        y_list = []
        for line in lines:
            elems = line.split("\t")
            assert (len(elems) == 2)
            update_data = self.non_char.sub("", elems[0].lower())
            segmented_sentence = " ".join(self.language_processor.segment_chinese_sentence_without_dictionary(update_data))
            x_list.append(segmented_sentence)
            y_list.append(int(elems[1]))

        vectorizer = CountVectorizer(ngram_range=(1, 3), analyzer="word", tokenizer=space_tokenizer)
        x_list = vectorizer.fit_transform(x_list)

        lin_clf = svm.LinearSVC()
        lin_clf.fit(x_list, y_list)

        model_file = self.data_root + "/like_dislike_model.pickle"
        f = open(model_file, 'wb')
        pickle.dump([vectorizer, lin_clf], f)
        f.close()
