import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--batch_size", default=64, type=int,
                        help="Batch size per GPU/CPU for training.")
parser.add_argument("--data_dir", default=None, type=str, required=True,
                    help="The input data dir. Should contain the .tsv files (or other data files) for the task.")
parser.add_argument("--output_dir", default=None, type=str, required=True,
                        help="The output directory where the model predictions and checkpoints will be written.")
parser.add_argument("--model_name_or_path", default=None, type=str, required=True,
                    help="Path to pre-trained model or shortcut name selected in the list: ")
parser.add_argument("--num_train_epochs", default=3, type=int,
                    help="Total number of training epochs to perform.")
parser.add_argument("--do_train", action='store_true',
                    help="Whether to run training.")
parser.add_argument("--gpu", type=int, default=6,
                        help="GPU ")
parser.add_argument("--max_seq_length", default=128, type=int,
                        help="The maximum total input sequence length after tokenization. Sequences longer "
                             "than this will be truncated, sequences shorter will be padded.")
args = parser.parse_args()