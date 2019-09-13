import codecs
import io
import pickle
import torch
import torch.utils.data as data
import utils
from collections import defaultdict
from cut import Trie
from lstm_crf import BiLSTMCRF
from utils import BEGIN_TAG, MIDDLE_TAG, END_TAG, SINGLE_TAG, process_eng


class ChineseSegmentor():

    def __init__(self, model_file_path, char_dict_path, word_dict_path=None, emb_dim=128, hidden_dim=128):

        self.model_file_path = model_file_path
        self.char_dict_path = char_dict_path
        self.word_dict_path = word_dict_path

        with io.open(self.char_dict_path, 'rb') as f:
            self.char2index = pickle.load(f)

        self.device, gpu_ids = utils.get_available_devices()

        bilstm_crf = BiLSTMCRF(self.device, utils.tag_to_ix, len(self.char2index) + 2, emb_dim, hidden_dim)
        self.segmentor_model = utils.load_model(bilstm_crf, self.model_file_path, gpu_ids, return_step=False)
        self.segmentor_model = self.segmentor_model.to(self.device)
        self.segmentor_model.eval()

        self.userdict = Trie()
        self.userdict.add_dict(self.word_dict_path)

    def seg(self, text, user_dict=None):
        text = text.strip()
        if len(text) == 0:
            return []

        results = []

        if user_dict is None:
            new_dict = self.userdict
        else:
            new_dict = Trie()
            new_dict.add_dict_word(user_dict)

        # word_list = utils.get_word(text)
        word_list = []
        for i in text:
            word_list.append(i)
        # print(word_list)
        sentence_tensor = utils.prepare_sequence(word_list, self.char2index)
        # print((sentence_tensor))

        with torch.no_grad():
            sentence, text, mask = utils.collate_fn_without_label([(sentence_tensor, text)])
            batch_size, seq_len = sentence.shape
            nb_labels = len(utils.tag_to_ix)
            text_score = torch.zeros(batch_size, seq_len, nb_labels).float()
            for i in range(batch_size):
                matchs = new_dict.cut(text[i])
                matchs.extend(process_eng(text[i]))
                # print(matchs)
                for m in matchs:
                    weight = new_dict.get_weight(m[2]) * 10.0
                    if len(m[2]) == 1:
                        text_score[i, m[0], utils.tag_to_ix[SINGLE_TAG]] = weight
                    elif len(m[2]) == 2:
                        text_score[i, m[0], utils.tag_to_ix[BEGIN_TAG]] = weight
                        text_score[i, m[0] + 1, utils.tag_to_ix[END_TAG]] = weight
                    else:
                        text_score[i, m[0], utils.tag_to_ix[BEGIN_TAG]] = weight
                        text_score[i, m[1] - 1, utils.tag_to_ix[END_TAG]] = weight
                        text_score[i, m[0] + 1:m[1] - 1, utils.tag_to_ix[MIDDLE_TAG]] = weight

            masks = mask.to(self.device)
            sen = sentence.to(self.device)
            temp_pred = self.segmentor_model(sen, mask=masks, text=text_score)[1]
            for i in range(batch_size):
                result = ''
                for j in range(len(temp_pred[i])):
                    # if text[i][j] == ' ':
                    #     continue
                    result += text[i][j]
                    if temp_pred[i][j] == 4 or temp_pred[i][j] == 3:
                        results.append(result)
                        result = ''
        return results

    def get(self, text, user_dict=None):
        if user_dict is None:
            new_dict = self.userdict
        else:
            new_dict = Trie()
            new_dict.add_dict_word(user_dict)

        matchs = new_dict.cut(text)
        graph = defaultdict(dict)
        temp_dict = []
        for j in range(len(text)):
            graph[j][j + 1] = 1.0
        for m in matchs:
            graph[m[0]][m[1]] = new_dict.get_weight(m[2]) * len(m[2])
            temp_dict.append(m[2])
        route = {}
        route[len(text)] = (0, 0)

        for idx in range(len(text) - 1, -1, -1):
            m = [((graph.get(idx).get(k) + route[k][0]), k)
                 for k in graph.get(idx).keys()]
            mm = max(m)
            route[idx] = (mm[0], mm[1])

        index = 0
        path = [index]
        result = []
        while index < len(text):
            ind_y = route[index][1]
            path.append(ind_y)
            words=text[index:ind_y]
            if words in temp_dict and words not in result:
                result.append(words)
            index = ind_y

        return result

    def test_file_with_label(self, input_filename, output_filename):

        F1 = 0.0
        count = 0

        test_data, _ = utils.load_data_with_label(input_filename, self.char2index, False)
        test_dataset = utils.Dataset(test_data)
        test_loader = data.DataLoader(test_dataset, batch_size=len(test_dataset), shuffle=False,
                                       collate_fn=utils.collate_fn_with_label)

        with torch.no_grad():
            with io.open(input_filename, 'r', encoding='utf8') as f:
                with io.open(output_filename, 'w', encoding='utf8') as y:
                    for sentence, label, mask in test_loader:
                        line = f.readline()
                        line = line.strip('\n')
                        line = line.strip(' ')
                        line = line.replace(' ', '')
                        while not line.strip():
                            line = f.readline()
                            line = line.strip('\n')
                            line = line.strip(' ')
                            line = line.replace(' ', '')
                        masks = mask.to(self.device)
                        sen = sentence.to(self.device)
                        temp_pred = self.segmentor_model(sen, masks)[1]

                        for i in range(len(label)):
                            count += 1
                            temppred = torch.tensor(temp_pred[i], dtype=torch.long)
                            tempgold = label[i][:torch.sum(masks[i] > 0).item()]
                            tempf = utils.compute_f1(tempgold, temppred)
                            F1 += tempf

                            results = []
                            result = ''
                            for j in range(len(temp_pred[i])):
                                result += line[j]
                                if temp_pred[i][j] == 4 or temp_pred[i][j] == 3:
                                    results.append(result)
                                    result = ''
                            y.write(" ".join(results) + "\n")

        F1 = F1 / count
        print(F1)

    def test_file_without_label(self, input_filename, output_filename):

        test_data = utils.load_data_without_label(input_filename, self.char2index)
        test_dataset = utils.Dataset(test_data)
        test_loader = data.DataLoader(test_dataset, batch_size=len(test_dataset), shuffle=False,
                                      collate_fn=utils.collate_fn_without_label)

        f = codecs.open(output_filename, 'w', 'utf-8')
        with torch.no_grad():
            for sentence, text, mask in test_loader:
                masks = mask.to(self.device)
                sen = sentence.to(self.device)
                temp_pred = self.segmentor_model(sen, masks)[1]
                for i in range(len(test_dataset)):
                    results = []
                    result = ''
                    for j in range(len(temp_pred[i])):
                        result += text[i][j]
                        if temp_pred[i][j] == 4 or temp_pred[i][j] == 3:
                            results.append(result)
                            result = ''
                    f.write(" ".join(results) + "\n")
        f.close()
