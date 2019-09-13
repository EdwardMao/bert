'''
For dataset, one sentence is one line, words are split by space
1. run util.py to get dataset
2. run train.py --name train
3. run test.py --name test
'''
name = "train"
learning_rate = 1e-3
embedding_dim = 256
hidden_dim = 256
batch_size = 1
epochs = 5
drop_out = 0.1
random_seed = 224
eval_during_train = True
eval_steps = 2
load_path = None
test_has_label = True
save_dir = "./save/"
train_file = './data/train.tsv'
dev_file = './data/dev.tsv'
test_file = './data/test.tsv'
test_output_file = "./data/test_output.tsv"
model_path = './data/best.pth.tar'
word_to_ix_path = './data/word_to_ix.p'