import io
import re
import torch
import string
import torch.utils.data as data

START_TAG = '<'
STOP_TAG = '>'
PAD = 'PAD'
BEGIN_TAG = 'B'
MIDDLE_TAG = 'M'
END_TAG = 'E'
SINGLE_TAG = 'S'
tag_to_ix = {PAD: 0, BEGIN_TAG: 1, MIDDLE_TAG: 2, END_TAG: 3, SINGLE_TAG: 4, START_TAG: 5, STOP_TAG: 6}


class Dataset(data.Dataset):

    def __init__(self, data_seq):
        self.data_seq = data_seq
        self.num_total = len(self.data_seq)

    def __getitem__(self, index):
        src_seq = self.data_seq[index][0]
        src_label = self.data_seq[index][1]
        return src_seq, src_label

    def __len__(self):
        return self.num_total


def get_available_devices():
    """Get IDs of all available GPUs.

    Returns:
        device (torch.device): Main device (GPU 0 or CPU).
        gpu_ids (list): List of IDs of all GPUs that are available.
    """
    gpu_ids = []
    if torch.cuda.is_available():
        gpu_ids += [gpu_id for gpu_id in range(torch.cuda.device_count())]
        device = torch.device('cuda:{}'.format(gpu_ids[0]))
        torch.cuda.set_device(device)
    else:
        device = torch.device('cpu')

    return device, gpu_ids


def load_model(model, checkpoint_path, gpu_ids, return_step=True):
    """Load model parameters from disk.

    Args:
        model (torch.nn.DataParallel): Load parameters into this model.
        checkpoint_path (str): Path to checkpoint to load.
        gpu_ids (list): GPU IDs for DataParallel.
        return_step (bool): Also return the step at which checkpoint was saved.

    Returns:
        model (torch.nn.DataParallel): Model loaded from checkpoint.
        step (int): Step at which checkpoint was saved. Only if `return_step`.
    """
    device = 'cuda:{}'.format(gpu_ids[0]) if gpu_ids else 'cpu'
    ckpt_dict = torch.load(checkpoint_path, map_location=device)

    # Build model, load parameters
    model.load_state_dict(ckpt_dict['model_state'])

    if return_step:
        step = ckpt_dict['step']
        return model, step

    return model


def get_word(sentence):
    """
    sentence to wordlist get words in sentence
    input: str. with space
    output: list of word

    """
    word_list = []
    sentence = re.sub('｀', '“', sentence)
    sentence = re.sub('＇', '”', sentence)
    sentence = ''.join(sentence.split(' '))
    for i in sentence:
        word_list.append(i)
    return word_list


def get_str(sentence):
    """
    change sentence to label
    sentence  to label
    input: str
    output: []
    """
    output_str = []
    sentence = re.sub('  ', ' ', sentence)

    list = sentence.split(' ')

    for i in range(len(list)):
        if len(list[i]) == 1:
            output_str.append('S')
        elif len(list[i]) == 2:
            output_str.append('B')
            output_str.append('E')
        elif len(list[i]) > 2:
            num = len(list[i]) - 2
            output_str.append('B')
            output_str.extend('M' * num)
            output_str.append('E')

    return output_str


def prepare_sequence(seq, to_ix):
    """
    change word to number
    wordlist to vec
    input: list of word, dict, unknown word is 1
    output: tensor [numbers]
    """
    idxs = [to_ix[w] if w in to_ix else 1 for w in seq]
    return torch.tensor(idxs, dtype=torch.long)


def read_file(filename):
    """
    file to content and label
    output: [[],[]]

    """
    word = []
    content = []
    label = []
    with io.open(filename, 'r', encoding='utf8') as f:
        for line in f:
            line = line.strip('\n')
            line = line.strip(' ')
            if line.strip():
                word_list = get_word(line)
                lable_list = get_str(line)
                word.extend(word_list)
                content.append(word_list)
                label.append(lable_list)

    return word, content, label


def load_data_without_label(filename, word_to_ix):

    data_list = []
    with io.open(filename, 'r', encoding='utf8') as f:
        for line in f:
            line = line.strip('\n')
            line = line.strip(' ')
            line = line.replace(' ', '')
            if line.strip():
                word_list = get_word(line)
                sen = prepare_sequence(word_list, word_to_ix)
                data_list.append((sen, line))

    return data_list


def load_data_with_label(filename, word_to_ix, update_vocab=True):

    _, content, label = read_file(filename)
    data_list = []

    for i in range(len(label)):
        if update_vocab:
            for word in content[i]:
                if word not in word_to_ix:
                    word_to_ix[word] = len(word_to_ix) + 2

        sen = prepare_sequence(content[i], word_to_ix)
        targets = torch.tensor([tag_to_ix[t] for t in label[i]], dtype=torch.long)
        data_list.append((sen, targets))

    return data_list, word_to_ix


def collate_fn_with_label(input_data):
    def merge(sequence):
        lengths = [len(seq) for seq in sequence]
        padded_seqs = torch.zeros(len(sequence), 256).long()
        mask = torch.zeros(len(sequence), 256).float()
        for i in range(len(sequence)):
            end = lengths[i]
            if end > 255:
                end = 255
            padded_seqs[i, :end] = sequence[i][:end]
            mask[i, :end] = 1.0
        return padded_seqs, mask

    data_seq, data_label = zip(*input_data)
    data_seq, mask = merge(data_seq)
    data_label, _ = merge(data_label)
    return data_seq, data_label, mask


def collate_fn_without_label(input_data):

    def merge(sequence):
        lengths = [len(seq) for seq in sequence]
        padded_seqs = torch.zeros(len(sequence), 256).long()
        mask = torch.zeros(len(sequence), 256).float()
        for i in range(len(sequence)):
            end = lengths[i]
            if end > 255:
                end = 255
            padded_seqs[i, :end] = sequence[i][:end]
            mask[i, :end] = 1.0
        return padded_seqs, mask

    data_seq, data_label = zip(*input_data)
    data_seq, mask = merge(data_seq)
    return data_seq, data_label, mask


def compute_f1(a_gold, a_pred):
    """
    compute f1
    """
    num_same = 0
    pred_toks = []
    gold_toks = []

    start_c = False
    for i in range(len(a_pred)):
        if a_gold[i] == 4 and a_pred[i] == 4:
            num_same += 1
        if a_gold[i] == 1 and a_pred[i] == 1:
            start_c = True
        if a_gold[i] == 3 and a_pred[i] != 3:
            start_c = False
        if a_gold[i] != 3 and a_pred[i] == 3:
            start_c = False
        if a_gold[i] == 3 and a_pred[i] == 3 and start_c == True:
            num_same += 1
            start_c = False
        if a_gold[i] == 1 or a_gold[i] == 4:
            gold_toks.append(i)
        if a_pred[i] == 1 or a_pred[i] == 4:
            pred_toks.append(i)

    if len(pred_toks) == 0 or len(gold_toks) == 0:
        return 0

    precision = 1.0 * num_same / len(pred_toks)
    recall = 1.0 * num_same / len(gold_toks)
    if precision + recall == 0:
        return 0

    f1 = (2 * precision * recall) / (precision + recall)
    return f1

def process_eng(text):
    i = 0
    result = []
    while re.search("[a-zA-Z0-9' %s]+"%string.punctuation, text[i:]):
        search_result = re.search("[a-zA-Z0-9' %s]+"%string.punctuation, text[i:]).span()
        start = search_result[0] + i
        end = search_result[1] + i
        if end - start > 1 or text[start] == ' ':
            result.append((start,end,text[start:end]))
        i = end
    return result
