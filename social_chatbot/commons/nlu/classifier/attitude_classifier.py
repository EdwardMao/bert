import codecs
import pickle
import re
import sys

from collections import defaultdict
from commons.nlu.classifier.classifier import BaseClassifier
from enum import Enum


class YesNoLabel(Enum):

    Yes = 1
    No = 2
    Unclear = 3


class LikeDisLikeLabel(Enum):

    Like = 1
    DisLike = 2


def generate_tokenized_sentence_without_punctuation(sentence):

    tokenized_without_punctuation = []
    for token in sentence.token_list:
        if token.pos != 'wp':
            tokenized_without_punctuation.append(token.original_text)
    return tokenized_without_punctuation


class YesNoClassifier(BaseClassifier):

    def __init__(self, attitude_classifier_configure):

        super().__init__()
        self.data_root = attitude_classifier_configure.data_root
        self.model_path = attitude_classifier_configure.data_root + "/yes_no_model.pickle"
        f = open(self.model_path, 'rb')
        [self.vectorizer, self.model] = pickle.load(f)
        f.close()
        self.confidence = attitude_classifier_configure.confidence

        self.exact_match_dict = defaultdict()
        self.exact_match_file = attitude_classifier_configure.data_root + "/yes_no_data.tsv"
        self.non_char = re.compile("([^\u4E00-\u9FD5a-zA-Z0-9])")
        lines = codecs.open(self.exact_match_file, 'r', 'utf-8').read().splitlines()
        for line in lines:
            elems = line.split("\t")
            update_sentence = self.non_char.sub("", elems[0].lower())
            if update_sentence in self.exact_match_dict and int(elems[1]) != self.exact_match_dict[update_sentence]:
                sys.stderr.write("Conflict Label for sentence [%s]!\n" % update_sentence)
                continue

            self.exact_match_dict[update_sentence] = int(elems[1])

    def classify(self, query):

        for sentence in query.sentence_list:
            tokenized_sentence = generate_tokenized_sentence_without_punctuation(sentence)
            concat_sentence = "".join(tokenized_sentence)
            if concat_sentence in self.exact_match_dict:
                if self.exact_match_dict[concat_sentence] == 1:
                    sentence.yesno_result = YesNoLabel.Yes
                    sentence.yesno_result_with_confidence = YesNoLabel.Yes
                    sentence.yesno_probability = {YesNoLabel.Yes: 100, YesNoLabel.No: 0, YesNoLabel.Unclear: 0}
                    continue
                elif self.exact_match_dict[concat_sentence] == 2:
                    sentence.yesno_result = YesNoLabel.No
                    sentence.yesno_result_with_confidence = YesNoLabel.No
                    sentence.yesno_probability = {YesNoLabel.Yes: 0, YesNoLabel.No: 100, YesNoLabel.Unclear: 0}
                    continue
                else:
                    sentence.yesno_result = YesNoLabel.Unclear
                    sentence.yesno_result_with_confidence = YesNoLabel.Unclear
                    sentence.yesno_probability = {YesNoLabel.Yes: 0, YesNoLabel.No: 0, YesNoLabel.Unclear: 100}
                    continue

            concat_sentence_withspace = " ".join(tokenized_sentence)
            feature_vector = self.vectorizer.transform([concat_sentence_withspace])
            result = self.model.decision_function(feature_vector)[0]
            sentence.yesno_probability = {YesNoLabel.Yes: result[0],
                                          YesNoLabel.No: result[1],
                                          YesNoLabel.Unclear: result[2]}

            result = self.model.predict(feature_vector)[0]
            if result == 1:
                sentence.yesno_result = YesNoLabel.Yes
                if sentence.yesno_probability[YesNoLabel.Yes] > self.confidence:
                    sentence.yesno_result_with_confidence = YesNoLabel.Yes
            elif result == 2:
                sentence.yesno_result = YesNoLabel.No
                if sentence.yesno_probability[YesNoLabel.No] > self.confidence:
                    sentence.yesno_result_with_confidence = YesNoLabel.No
            else:
                sentence.yesno_result = YesNoLabel.Unclear
                if sentence.yesno_probability[YesNoLabel.Unclear] > self.confidence:
                    sentence.yesno_result_with_confidence = YesNoLabel.Unclear


class LikeDislikeClassifier(BaseClassifier):

    def __init__(self, attitude_classifier_configure):

        super().__init__()
        self.data_root = attitude_classifier_configure.data_root
        self.model_path = attitude_classifier_configure.data_root + "/like_dislike_model.pickle"
        f = open(self.model_path, 'rb')
        [self.vectorizer, self.model] = pickle.load(f)
        f.close()
        self.confidence = attitude_classifier_configure.confidence

        self.exact_match_dict = defaultdict()
        self.exact_match_file = attitude_classifier_configure.data_root + "/like_dislike_data.tsv"
        lines = codecs.open(self.exact_match_file, 'r', 'utf-8').read().splitlines()
        for line in lines:
            elems = line.split("\t")
            update_sentence = elems[0].lower()
            if update_sentence in self.exact_match_dict and int(elems[1]) != self.exact_match_dict[update_sentence]:
                sys.stderr.write("Conflict Label for sentence [%s]!\n" % update_sentence)
                continue

            self.exact_match_dict[update_sentence] = int(elems[1])

    def classify(self, query):

        for sentence in query.sentence_list:
            tokenized_sentence = generate_tokenized_sentence_without_punctuation(sentence)
            concat_sentence = "".join(tokenized_sentence)

            if concat_sentence in self.exact_match_dict:
                if self.exact_match_dict[concat_sentence] == 0:
                    sentence.like_probability = {LikeDisLikeLabel.DisLike: -100, LikeDisLikeLabel.Like: 0}
                    sentence.like_result = LikeDisLikeLabel.DisLike
                    sentence.like_result_with_confidence = LikeDisLikeLabel.DisLike
                else:
                    sentence.like_probability = {LikeDisLikeLabel.DisLike: 0, LikeDisLikeLabel.Like: 100}
                    sentence.like_result = LikeDisLikeLabel.Like
                    sentence.like_result_with_confidence = LikeDisLikeLabel.Like

            concat_sentence_withspace = " ".join(tokenized_sentence)
            feature_vector = self.vectorizer.transform([concat_sentence_withspace])
            result = self.model.decision_function(feature_vector)[0]

            if result == self.model.intercept_[0]:
                sentence.like_probability = {LikeDisLikeLabel.Like: 0, LikeDisLikeLabel.DisLike: 0}
                sentence.like_result = LikeDisLikeLabel.Like

            if result > 0:
                sentence.like_probability = {LikeDisLikeLabel.Like: result, LikeDisLikeLabel.DisLike: 0}
                sentence.like_result = LikeDisLikeLabel.Like
                if result > self.confidence:
                    sentence.like_result_with_confidence = LikeDisLikeLabel.Like
            else:
                sentence.like_probability = {LikeDisLikeLabel.DisLike: -result, LikeDisLikeLabel.Like: 0}
                sentence.like_result = LikeDisLikeLabel.DisLike
                if -result > self.confidence:
                    sentence.like_result_with_confidence = LikeDisLikeLabel.DisLike
