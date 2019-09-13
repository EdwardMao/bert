import codecs
import json
import logging
import os
import pickle
import re
import sys

from collections import defaultdict
from commons.nlu.classifier.classifier import BaseClassifier
from enum import Enum

class DialogActLabel(Enum):

    Statement = 0
    Question = 1
    Exclamatory = 2
    Oral = 3
    Imperative = 4
    Initiation = 5
    Ending = 6
    Gratitude = 7


class DialogActClassifier(BaseClassifier):

    def __init__(self, dialog_act_classifier_configure):

        super().__init__()
        self.data_root = dialog_act_classifier_configure.data_root
        self.model_path = self.data_root + "/dialog_act_model.pickle"
        f = open(self.model_path, 'rb')
        [self.vectorizer, self.model] = pickle.load(f)
        f.close()
        self.non_char = re.compile("([^\u4E00-\u9FD5a-zA-Z0-9])")
        self.confidence = dialog_act_classifier_configure.confidence

    def classify(self, query):

        X = []
        for sentence in query.sentence_list:
            segmented_sentence = []
            for token in sentence.token_list:
                update_token = self.non_char.sub("", token.original_text.lower())
                segmented_sentence.append(update_token)
            segmented_sentence = " ".join(segmented_sentence)
            # print(segmented_sentence)
            X.append(segmented_sentence)
        # print(X)

        X = self.vectorizer.transform(X)
        decision_detail = self.model.decision_function(X)
        decision = self.model.predict(X)

        for i in range(len(query.sentence_list)):
            query.sentence_list[i].dialog_act_probability = {DialogActLabel.Statement: decision_detail[i][0],
                                                             DialogActLabel.Question: decision_detail[i][1],
                                                             DialogActLabel.Exclamatory: decision_detail[i][2],
                                                             DialogActLabel.Oral: decision_detail[i][3],
                                                             DialogActLabel.Imperative: decision_detail[i][4],
                                                             DialogActLabel.Initiation: decision_detail[i][5],
                                                             DialogActLabel.Ending: decision_detail[i][6],
                                                             DialogActLabel.Gratitude: decision_detail[i][7]}
            if decision[i] == 0:
                query.sentence_list[i].dialog_act_result = DialogActLabel.Statement
                if query.sentence_list[i].dialog_act_probability[DialogActLabel.Statement] > self.confidence:
                    query.sentence_list[i].dialog_act_result_with_confidence = DialogActLabel.Statement
            elif decision[i] == 1:
                query.sentence_list[i].dialog_act_result = DialogActLabel.Question
                if query.sentence_list[i].dialog_act_probability[DialogActLabel.Question] > self.confidence:
                    query.sentence_list[i].dialog_act_result_with_confidence = DialogActLabel.Question
            elif decision[i] == 2:
                query.sentence_list[i].dialog_act_result = DialogActLabel.Exclamatory
                if query.sentence_list[i].dialog_act_probability[DialogActLabel.Exclamatory] > self.confidence:
                    query.sentence_list[i].dialog_act_result_with_confidence = DialogActLabel.Exclamatory
            elif decision[i] == 3:
                query.sentence_list[i].dialog_act_result = DialogActLabel.Oral
                if query.sentence_list[i].dialog_act_probability[DialogActLabel.Oral] > self.confidence:
                    query.sentence_list[i].dialog_act_result_with_confidence = DialogActLabel.Oral
            elif decision[i] == 4:
                query.sentence_list[i].dialog_act_result = DialogActLabel.Imperative
                if query.sentence_list[i].dialog_act_probability[DialogActLabel.Imperative] > self.confidence:
                    query.sentence_list[i].dialog_act_result_with_confidence = DialogActLabel.Imperative
            elif decision[i] == 5:
                query.sentence_list[i].dialog_act_result = DialogActLabel.Initiation
                if query.sentence_list[i].dialog_act_probability[DialogActLabel.Initiation] > self.confidence:
                    query.sentence_list[i].dialog_act_result_with_confidence = DialogActLabel.Initiation
            elif decision[i] == 6:
                query.sentence_list[i].dialog_act_result = DialogActLabel.Ending
                if query.sentence_list[i].dialog_act_probability[DialogActLabel.Ending] > self.confidence:
                    query.sentence_list[i].dialog_act_result_with_confidence = DialogActLabel.Ending
            elif decision[i] == 7:
                query.sentence_list[i].dialog_act_result = DialogActLabel.Gratitude
                if query.sentence_list[i].dialog_act_probability[DialogActLabel.Gratitude] > self.confidence:
                    query.sentence_list[i].dialog_act_result_with_confidence = DialogActLabel.Gratitude
            