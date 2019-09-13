from config import *
import argparse

parser = argparse.ArgumentParser('Train a BiLSTM-CRF model')

# common
parser.add_argument('--metric_name',
                    type=str,
                    default='F1',
                    help='Name of dev metric to determine best checkpoint.')

parser.add_argument('--name',
                    '-n',
                    type=str,
                    default=name,
                    help='Name to identify training or test run.')

parser.add_argument('--save_dir',
                    type=str,
                    default=save_dir,
                    help='Base directory for saving information.')

parser.add_argument('--train_file',
                    type=str,
                    default=train_file,
                    help='Path to file with train data.')

parser.add_argument('--dev_file',
                    type=str,
                    default=dev_file,
                    help='Path to file with dev data')

parser.add_argument('--test_file',
                    type=str,
                    default=test_file,
                    help='Path to file with test data')

parser.add_argument('--test_has_label',
                    type=str,
                    default=test_has_label,
                    help='whether test data has label')

parser.add_argument('--test_output_file',
                    type=str,
                    default=test_output_file,
                    help='Path to file saving the test output')

parser.add_argument('--vocab_file',
                    type=str,
                    default=word_to_ix_path,
                    help='Path to file with vocab2ix')


parser.add_argument('--model_path',
                    type=str,
                    default=model_path,
                    help='Path to model file')

parser.add_argument('--load_path',
                    type=str,
                    default=load_path,
                    help='Path to load as a model checkpoint.')

parser.add_argument('--lr',
                    type=float,
                    default=learning_rate,
                    help='Learning rate.')

parser.add_argument('--dropout',
                    type=float,
                    default=drop_out,
                    help='Dropout probability.')

parser.add_argument('--seed',
                    type=int,
                    default=random_seed,
                    help='Random seed for reproducibility.')

parser.add_argument('--dev',
                    type=bool,
                    default=eval_during_train,
                    help='Determine whether eval while training')

parser.add_argument('--eval_steps',
                    type=int,
                    default=eval_steps,
                    help='Number of steps between successive evaluations.')

parser.add_argument('--EMBEDDING_DIM',
                    type=int,
                    default=embedding_dim,
                    help='Embedding')

parser.add_argument('--HIDDEN_DIM',
                    type=int,
                    default=hidden_dim,
                    help='hidden')

parser.add_argument('--num_epochs',
                    type=int,
                    default=epochs,
                    help='Number of epochs for which to train. Negative means forever.')

parser.add_argument('--batch_size',
                    type=int,
                    default=batch_size,
                    help='Batch size per GPU. Scales automatically when multiple GPUs are available.')

args = parser.parse_args()
args.maximize_metric = True
