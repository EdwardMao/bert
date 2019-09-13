import codecs
import globals
import logging
import os
import pickle
import re
import sys

from commons.utils import space_tokenizer, get_files
from commons.nlu.classifier.question_type_classifier import question_feature_extractor
from collections import defaultdict
from offline.tools.offline_tools import OfflineTools
from sklearn.feature_extraction.text import CountVectorizer
from sklearn import svm


class QuestionClassifierPipeline(OfflineTools):

    def __init__(self, local_configure):

        super().__init__()
        self.exe_type = local_configure["exe_type"]
        self.data_root = local_configure["data_root"]
        self.surround_num = local_configure["surround_num"]
        self.n_gram = local_configure["n_gram"]
        self.raw_data = local_configure["data_root"] + "/raw_data/"
        self.labeled_data = local_configure["data_root"] + "/labeled_data/"
        self.language_processor = globals.nlp_processor
        self.non_char = re.compile("([^\u4E00-\u9FD5a-zA-Z0-9])")
        self.system_logger = logging.getLogger("system_log")

        self.default_label = defaultdict(str)

        self.default_label["杂.txt"] = -1
        self.default_label["那.txt"] = -1
        self.default_label["哪有.txt"] = -1

        self.default_label["啥时候.txt"] = 2
        self.default_label["什么时候.txt"] = 2

        self.default_label["在哪.txt"] = 3
        self.default_label["住哪.txt"] = 3

        self.default_label["何在.txt"] = 3

        self.default_label["何方.txt"] = 3
        self.default_label["何用.txt"] = 6
        self.default_label["做啥.txt"] = 6

        self.default_label["去哪.txt"] = 3
        self.default_label["哪儿.txt"] = 3
        self.default_label["哪去.txt"] = 3
        self.default_label["哪的.txt"] = 3
        self.default_label["哪种.txt"] = 3
        self.default_label["哪里.txt"] = 3

        self.default_label["怎么.txt"] = 5
        self.default_label["怎样.txt"] = 5
        self.default_label["咋办.txt"] = 5
        self.default_label["咋样.txt"] = 5
        self.default_label["如何.txt"] = 5
        self.default_label["怎么办.txt"] = 5
        self.default_label["怎么样.txt"] = 5

        self.default_label["何为.txt"] = 6
        self.default_label["什么.txt"] = 6
        self.default_label["什麼.txt"] = 6
        self.default_label["怕啥.txt"] = 6
        self.default_label["是啥.txt"] = 6
        self.default_label["有何.txt"] = 6
        self.default_label["有啥.txt"] = 6
        self.default_label["有嘛.txt"] = 6
        self.default_label["玩啥.txt"] = 6
        self.default_label["神么.txt"] = 6
        self.default_label["神马.txt"] = 6
        self.default_label["肿么.txt"] = 5
        self.default_label["要啥.txt"] = 6
        self.default_label["说啥.txt"] = 6
        self.default_label["说的啥.txt"] = 6
        self.default_label["何物.txt"] = 6
        self.default_label["干吗.txt"] = 6
        self.default_label["干啥.txt"] = 6
        self.default_label["干嘛.txt"] = 6
        self.default_label["啥歌.txt"] = 6
        self.default_label["啥玩意.txt"] = 6
        self.default_label["啥用.txt"] = 6
        self.default_label["啥.txt"] = 6
        self.default_label["啥专业.txt"] = 6
        self.default_label["啥子意思.txt"] = 6
        self.default_label["啥意思.txt"] = 6
        self.default_label["吃啥.txt"] = 6
        self.default_label["吃的啥.txt"] = 6

        self.default_label["为什么.txt"] = 9
        self.default_label["为撒子.txt"] = 9
        self.default_label["咋.txt"] = 9
        self.default_label["咋不.txt"] = 9
        self.default_label["何必.txt"] = 9
        self.default_label["为何.txt"] = 9
        self.default_label["为啥.txt"] = 9
        self.default_label["为嘛.txt"] = 9
        self.default_label["为毛.txt"] = 9

        self.default_label["哪.txt"] = 11
        self.default_label["哪个.txt"] = 11
        self.default_label["哪些.txt"] = 11
        self.default_label["哪国.txt"] = 11
        self.default_label["哪天.txt"] = 2
        self.default_label["哪座.txt"] = 11
        self.default_label["哪方面.txt"] = 11
        self.default_label["哪本.txt"] = 11
        self.default_label["哪样.txt"] = 11
        self.default_label["哪款.txt"] = 11

        self.default_label["谁.txt"] = 12

        self.default_label["几.txt"] = 13
        self.default_label["几个.txt"] = 13
        self.default_label["几人.txt"] = 13
        self.default_label["几件.txt"] = 13
        self.default_label["几分.txt"] = 13
        self.default_label["几号.txt"] = 2
        self.default_label["几小时.txt"] = 13
        self.default_label["几岁.txt"] = 13
        self.default_label["几年.txt"] = 13
        self.default_label["几本.txt"] = 13
        self.default_label["几次.txt"] = 13
        self.default_label["几点.txt"] = 2
        self.default_label["多.txt"] = 13
        self.default_label["多久.txt"] = 13
        self.default_label["多大.txt"] = 13
        self.default_label["多少.txt"] = 13
        self.default_label["多懒.txt"] = 13
        self.default_label["多矮.txt"] = 13
        self.default_label["多重要.txt"] = 13
        self.default_label["多长.txt"] = 13
        self.default_label["多高.txt"] = 13

        self.label2str = defaultdict(str)
        self.label2str[1]= "YesNo"
        self.label2str[2] = "When"
        self.label2str[3] = "Where"
        self.label2str[5] = "How"
        self.label2str[6] = "What"
        self.label2str[8] = "Choose"
        self.label2str[9] = "Why"
        self.label2str[10] = "Rhetorical"
        self.label2str[11] = "Which"
        self.label2str[12] = "Who"
        self.label2str[13] = "Howmany"

        self.str2label = defaultdict(int)
        self.str2label["YesNo"] = 1
        self.str2label["What"] = 2
        self.str2label["Who"] = 3
        self.str2label["When"] = 4
        self.str2label["Where"] = 5
        self.str2label["Which"] = 6
        self.str2label["How"] = 7
        self.str2label["Why"] = 8
        self.str2label["Howmany"] = 9
        self.str2label["Rhetorical"] = 10
        self.str2label["Choose"] = 11


        pass

    def execute(self):

        if self.exe_type == "generate_data":
            self.generate_label_data()
        elif self.exe_type == "train":
            self.train_model()
        pass

    def generate_label_data(self):

        labeled_data = defaultdict(list)
        all_files = get_files(self.raw_data, r'.*txt')
        for filename in all_files:
            basename = os.path.basename(filename)

            lines = codecs.open(filename, 'r', 'utf-8').read().splitlines()
            for line in lines:
                elems = line.strip().split("\t")
                if len(elems) == 2 and int(elems[1]) != 4:
                    labeled_data[int(elems[1])].append(elems[0])
                else:
                    if self.default_label[basename] == -1:
                        log_str = "%s file has no default label value or given label value at line [%s]\n" \
                                  % (basename, line)
                        sys.stderr.write(log_str)
                        self.system_logger.info(log_str)
                        continue
                    labeled_data[self.default_label[basename]].append(elems[0])

        labeled_files = get_files(self.raw_data, r'.*tsv')
        for filename in labeled_files:
            label = -1
            if filename.find("反问句") >= 0:
                label = 10
            elif filename.find("是非问句") >= 0:
                label = 1
            elif filename.find("选择问句") >= 0:
                label = 8
            else:
                continue

            lines = codecs.open(filename, 'r', 'utf-8').read().splitlines()
            for line in lines:
                elems = line.strip().split("\t")
                labeled_data[label].append(elems[0].strip())

        for label, sentence_list in labeled_data.items():
            filename = self.labeled_data + self.label2str[label] + ".tsv"
            f = codecs.open(filename, 'w', 'utf-8')
            for s in sentence_list:
                f.write("%s\t%d\n" % (s, self.str2label[self.label2str[label]]))
            f.close()

        for label, sentence_list in labeled_data.items():
            filename = self.labeled_data + self.label2str[label] + "_feature.tsv"
            f = codecs.open(filename, 'w', 'utf-8')
            for s in sentence_list:
                query = self.language_processor.generate_query(s)
                output_str = []
                for sentence in query.sentence_list[:1]:
                    for token in sentence.token_list:
                        output_str.append(token.original_text + "/" + token.pos + "/" + str(token.arc_head) + "/" + token.arc_relation)
                f.write("%s\n" % " ".join(output_str))
            f.close()
        pass

    def train_model(self):

        all_files = get_files(self.labeled_data, r'.*tsv')
        X_list = []
        y_label = []
        for filename in all_files:
            if filename.find("feature") >= 0:
                continue

            lines = codecs.open(filename, 'r', 'utf-8').read().splitlines()
            sys.stdout.write("Processing [%s] and its training cases is [%d]\n" % (filename, len(lines)))
            for line in lines:
                elems = line.strip().split("\t")
                if len(elems) != 2:
                    log_str = "[%s] is not 2 columns\n" % line
                    self.system_logger.info(log_str)
                    sys.stderr.write(log_str)
                    continue
                query = self.language_processor.generate_query(elems[0])
                X_list.append(" ".join(question_feature_extractor(query.sentence_list[0],
                                                                  self.surround_num, self.n_gram)))
                y_label.append(int(elems[1]))

        vectorizer = CountVectorizer(ngram_range=(1, 1), analyzer="word", tokenizer=space_tokenizer)
        x_list = vectorizer.fit_transform(X_list)

        lin_clf = svm.LinearSVC(max_iter=1000000)
        lin_clf.fit(x_list, y_label)

        model_file = self.data_root + "/question_type_model.pickle"
        f = open(model_file, 'wb')
        pickle.dump([vectorizer, lin_clf], f)
        f.close()

        pass