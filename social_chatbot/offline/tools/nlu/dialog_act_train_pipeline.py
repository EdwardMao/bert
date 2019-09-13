import codecs
import json
import logging
import os
import globals
import pickle
import re
import sys
import numpy as np

from commons.nlu.language_processor import LanguageProcessor
from commons.nlu.schema.query import Query
from commons.utils import space_tokenizer
from configures import NLUConfigure
from offline.tools.offline_tools import OfflineTools
from sklearn.feature_extraction.text import CountVectorizer
from sklearn import svm


class DialogActClassifierPipeline(OfflineTools):

    def __init__(self, local_configure):

        super().__init__()
        self.exe_type = local_configure["exe_type"]
        self.data_root = local_configure["data_root"]
        self.dialog_act_train_file = local_configure["data_root"] + "train.tsv"
        self.dialog_act_test_file = local_configure["data_root"] + "test.tsv"
        self.model_file = self.data_root + "/dialog_act_model.pickle"
        # self.nlu_configure = NLUConfigure(**global_configure["nlu_configure"])
        # self.language_processor = LanguageProcessor(self.nlu_configure)
        self.language_processor = globals.nlp_processor
        self.non_char = re.compile("([^\u4E00-\u9FD5a-zA-Z0-9])")

    def execute(self):

        if self.exe_type == "train":
            self._train_dialog_act_classifier()
            self._test_dialog_act_classifier()
        elif self.exe_type == "test":
            self._test_dialog_act_classifier()
        else:
            print("Wrong exe_type!! Only train and test are allowed.")

    def _train_dialog_act_classifier(self):

        sys.stdout.write("Start Training Dialog Act Classifier!\n")
        lines = codecs.open(self.dialog_act_train_file, 'r', 'utf-8').read().splitlines()
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

        lin_clf = svm.LinearSVC(max_iter=5000)
        lin_clf.fit(X_list, Y_list)

        f = open(self.model_file, 'wb')
        pickle.dump([vectorizer, lin_clf], f)
        f.close()

    def _test_dialog_act_classifier(self):

        f = open(self.model_file, 'rb')
        [self.vectorizer, self.model] = pickle.load(f)
        f.close()
        X = []
        Y = []
        lines = codecs.open(self.dialog_act_test_file, 'r', 'utf-8').read().splitlines()
        for line in lines:
            elems = line.split("\t")
            assert(len(elems) == 2)
            update_data = self.non_char.sub("", elems[0].lower())
            # print(update_data)
            segmented_sentence = " ".join(self.language_processor.segment_chinese_sentence_without_dictionary(update_data))
            # print(segmented_sentence)
            X.append(segmented_sentence)
            Y.append(int(elems[1]))
        print(len(X))

        X = self.vectorizer.transform(X)
        Y_decision = self.model.decision_function(X)
        print(len(Y_decision))
        print(type(Y_decision[0]))
        Y_predict = self.model.predict(X)
        # print(len(Y_predict))
        assert(len(Y) == len(Y_predict))
        count = 0
        count_err_type = {}
        for i in range(len(Y)):
            if Y[i] == Y_predict[i]:
                count += 1
            else:
                count_err_type[Y[i]] = count_err_type.get(Y[i], 0) + 1
                # print("Label:", Y[i], "Predict:", Y_predict[i])
        print(Y.count(0), Y.count(1), Y.count(2), Y.count(3), Y.count(4), Y.count(5), Y.count(6), Y.count(7))
        count_type = {}
        for i in range(8):
            count_type[i] = Y.count(i)
            print(1 - count_err_type[i] / count_type[i])
        print(count_err_type)
        print(count/len(Y))