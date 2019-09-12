"""
The system trains BERT on the SNLI + MultiNLI (AllNLI) dataset
with softmax loss function. At every 1000 training steps, the model is evaluated on the
STS benchmark dataset
python training_nli_bert.py --data_dir ../data/MNLI/ --output_dir ./MNLIencodecls --model_name_or_path bert-base-chinese --max_seq_length 128 --gpu 6
"""
from torch.utils.data import DataLoader
import math

from sentence_transformers import models, losses
from sentence_transformers import SentencesDataset, LoggingHandler, SentenceTransformer
from sentence_transformers.evaluation import *
from sentence_transformers.readers import *
import logging
from datetime import datetime
from args import args
batch_size = args.batch_size

#### Just some code to print debug information to stdout
logging.basicConfig(format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO,
                    handlers=[LoggingHandler()])
#### /print debug information to stdout

# Read the dataset

nli_reader = ChineseDataReader(args.data_dir)
train_num_labels = nli_reader.get_num_labels()
model_save_path = args.output_dir

if args.do_train:



    # Use BERT for mapping tokens to embeddings
    word_embedding_model = models.BERT(args.model_name_or_path)

    # Apply mean pooling to get one fixed sized sentence vector
    pooling_model = models.Pooling(word_embedding_model.get_word_embedding_dimension(),
                                   pooling_mode_mean_tokens=True,
                                   pooling_mode_cls_token=False,
                                   pooling_mode_max_tokens=False)


    model = SentenceTransformer(modules=[word_embedding_model, pooling_model])


    # Convert the dataset to a DataLoader ready for training
    logging.info("Read train dataset")
    train_data = SentencesDataset(nli_reader.get_train_examples(args.data_dir), model=model)
    train_dataloader = DataLoader(train_data, shuffle=True, batch_size=batch_size)
    # train_loss = losses.SoftmaxLoss(model=model, sentence_embedding_dimension=model.get_sentence_embedding_dimension(), num_labels=train_num_labels)
    train_loss = losses.CosineSimilarityLoss(model=model)


    logging.info("Read dev dataset")
    dev_data = SentencesDataset(examples=nli_reader.get_dev_examples(args.data_dir), model=model)
    dev_dataloader = DataLoader(dev_data, shuffle=False, batch_size=batch_size)
    # evaluator = EmbeddingSimilarityEvaluator(dev_dataloader)
    evaluator = BinaryEmbeddingSimilarityEvaluator(dev_dataloader)

    # Configure the training
    num_epochs = args.num_train_epochs

    warmup_steps = math.ceil(len(train_dataloader) * num_epochs * 0.1) #10% of train data for warm-up
    logging.info("Warmup-steps: {}".format(warmup_steps))



    # Train the model
    model.fit(train_objectives=[(train_dataloader, train_loss)],
              evaluator=evaluator,
              epochs=num_epochs,
              evaluation_steps=1000,
              warmup_steps=warmup_steps,
              output_path=model_save_path
              )



##############################################################################
#
# Load the stored model and evaluate its performance on STS benchmark dataset
#
##############################################################################
model_save_path = args.output_dir
nli_reader = ChineseDataReader(args.data_dir)
model = SentenceTransformer(model_save_path)
test_data = SentencesDataset(examples=nli_reader.get_dev_examples(args.data_dir), model=model)
test_dataloader = DataLoader(test_data, shuffle=False, batch_size=batch_size)
# evaluator = EmbeddingSimilarityEvaluator(test_dataloader)
evaluator = BinaryEmbeddingSimilarityEvaluator(test_dataloader)

model.evaluate(evaluator)
