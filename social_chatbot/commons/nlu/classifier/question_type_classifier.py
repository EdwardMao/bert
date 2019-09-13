import codecs
import pickle
import re
import sys

from collections import defaultdict
from commons.nlu.classifier.classifier import BaseClassifier
from enum import Enum
from commons.utils import get_ngrams

yesno_keys = ["吗", "么", "吧", "嘛", "不", "没", "呢"]
yesno_keys2 = ["没有"]

choose_key = ["还是", "是"]

question_keys = ["干什么",
                 "怎",
                 "那",
                 "哪有",
                 "啥时候",
                 "在哪",
                 "住哪",
                 "何在",
                 "何方",
                 "何用",
                 "做啥",
                 "去哪",
                 "哪儿",
                 "哪去",
                 "哪的",
                 "哪种",
                 "哪里",
                 "怎么",
                 "怎样",
                 "咋办",
                 "咋样",
                 "如何",
                 "怎么办",
                 "怎么样",
                 "何为",
                 "什么",
                 "什麼",
                 "怕啥",
                 "是啥",
                 "有何",
                 "有啥",
                 "有嘛",
                 "玩啥",
                 "神么",
                 "神马",
                 "肿么",
                 "要啥",
                 "说啥",
                 "说的啥",
                 "何物",
                 "干吗",
                 "干啥",
                 "干嘛",
                 "啥歌",
                 "啥玩意",
                 "啥用",
                 "啥",
                 "啥专业",
                 "啥子意思",
                 "啥意思",
                 "吃啥",
                 "吃的啥",
                 "为什么",
                 "为撒子",
                 "咋",
                 "咋不",
                 "何必",
                 "为何",
                 "为啥",
                 "为嘛",
                 "为毛",
                 "哪",
                 "哪个",
                 "哪些",
                 "哪国",
                 "哪天",
                 "哪座",
                 "哪方面",
                 "哪本",
                 "哪样",
                 "哪款",
                 "谁",
                 "几",
                 "几个",
                 "幾個",
                 "几人",
                 "几件",
                 "几分",
                 "几号",
                 "几小时",
                 "几岁",
                 "几年",
                 "几本",
                 "几次",
                 "几点",
                 "多",
                 "多久",
                 "多大",
                 "多少",
                 "多懒",
                 "多矮",
                 "多重要",
                 "多长",
                 "多高"]


class QuestionLabel(Enum):
    YesNo = 1
    What = 2
    Who = 3
    When = 4
    Where = 5
    Which = 6
    How = 7
    Why = 8
    Howmany = 9
    Rhetorical = 10
    Choose = 11


def centralized_sentence(token_list, index, surround_num):

    if surround_num <= 1:
        return [token_list[index].orginal_text]

    update_str = []
    update_pos = []
    for i in range(surround_num):
        update_index = index - i - 1
        if update_index >= 0:
            update_str.insert(0, token_list[update_index].original_text)
            update_pos.insert(0, token_list[update_index].pos)
        else:
            if len(update_str) == 0:
                update_str.insert(0, "<START>")
            elif update_str[0] != "<START>":
                update_str.insert(0, "<START>")

            if len(update_pos) == 0:
                update_pos.insert(0, "<POSSTART>")
            elif update_pos[0] != "<POSSTART>":
                update_pos.insert(0, "<POSSTART>")

    update_str.append(token_list[index].original_text)
    update_pos.append(token_list[index].pos)

    for i in range(surround_num):
        update_index = index + i + 1
        if update_index >= len(token_list):
            if update_str[-1] != "<END>":
                update_str.append("<END>")
            if update_pos[-1] != "<POSEND>":
                update_pos.append("<POSEND>")
        else:
            update_str.append(token_list[update_index].original_text)
            update_pos.append(token_list[update_index].pos)

    return update_str, update_pos


def question_feature_extractor(sentence, surround_num, n_gram):

    feature_list = []
    key_word_index = []

    search_result = re.search(r'(.)[不|没|木](.)', sentence.raw_sentence, re.M | re.I)
    if search_result:
        if search_result.group(1) == search_result.group(2):
            feature_list.append("不|没|木_YES")
        else:
            feature_list.append("不|没|木_NO")
    else:
        feature_list.append("不|没|木_NO")

    found_yesno_keys = False
    for token in sentence.token_list[::-1]:
        if token.pos != "wp" and (token.word in yesno_keys or token.word in yesno_keys2):
            found_yesno_keys = True
            feature_list.append("yesno_keys_yes")
            break

    if not found_yesno_keys:
        feature_list.append("yesno_keys_no")

    feature_list.append(feature_list[-2] + "_" + feature_list[-1])

    if sentence.token_list[-1].pos == "wp" and sentence.token_list[-1].word == "?":
        feature_list.append("question_mark_yes")
    else:
        feature_list.append("question_mark_no")

    pos1 = sentence.raw_sentence.find("还是")
    if pos1 >= 0:
        feature_list.append("haishi_yes")
    else:
        feature_list.append("haishi_no")

    pos2 = sentence.raw_sentence.find("是")
    if pos2 >= 0:
        if pos2 == pos1 + 1:
            feature_list.append("shi_no")
        else:
            feature_list.append("shi_yes")
    else:
        feature_list.append("shi_no")

    feature_list.append(feature_list[-2] + "_" + feature_list[-1])

    for index, token in enumerate(sentence.token_list):
        if token.original_text in question_keys:
            key_word_index.append(index)
            feature_list.append("keyword_" + token.original_text)
            feature_list.append("keyword_" + token.pos)

    feature_list.append("%d_key_word" % len(key_word_index))

    if len(key_word_index) == 0:
        feature_list.append("no_key_word")
        feature_list.append("0_" + feature_list[0])
        feature_list.append("0_" + feature_list[1])
    else:
        feature_list.append("have_key_word")
        feature_list.append("1_" + feature_list[0])
        feature_list.append("1_" + feature_list[1])

    for index in key_word_index:
        sub_sentence, sub_pos = centralized_sentence(sentence.token_list, index, surround_num)
        str_ngrams = []
        pos_ngrams = []
        for i in range(1, n_gram+1):
            str_ngrams.extend(get_ngrams(sub_sentence, i))
            pos_ngrams.extend(get_ngrams(sub_pos, i))

        feature_list.extend(str_ngrams)
        feature_list.extend(pos_ngrams)

    return feature_list


class QuestionClassifier(BaseClassifier):

    def __init__(self, question_classifier_configure):
        super().__init__()
        self.data_root = question_classifier_configure.data_root
        self.model_path = question_classifier_configure.data_root + "/question_type_model.pickle"
        self.surround_num = question_classifier_configure.surround_num
        self.n_gram = question_classifier_configure.n_gram
        f = open(self.model_path, 'rb')
        [self.vectorizer, self.model] = pickle.load(f)
        f.close()
        pass

    def classify(self, query):

        for sentence in query.sentence_list:
            feature_list = question_feature_extractor(sentence, self.surround_num, self.n_gram)
            feature_str = " ".join(feature_list)
            feature_vector = self.vectorizer.transform([feature_str])
            result = self.model.decision_function(feature_vector)[0]
            sentence.question_type_probability = {QuestionLabel.YesNo: result[0],
                                                  QuestionLabel.What: result[1],
                                                  QuestionLabel.Who: result[2],
                                                  QuestionLabel.When: result[3],
                                                  QuestionLabel.Where: result[4],
                                                  QuestionLabel.Which: result[5],
                                                  QuestionLabel.How: result[6],
                                                  QuestionLabel.Why: result[7],
                                                  QuestionLabel.Howmany: result[8],
                                                  QuestionLabel.Rhetorical: result[9],
                                                  QuestionLabel.Choose: result[10]}

            result = self.model.predict(feature_vector)[0]
            sentence.question_type_result = QuestionLabel(result)
        pass
