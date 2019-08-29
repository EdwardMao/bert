"""
This basic example loads a pre-trained model from the web and uses it to
generate sentence embeddings for a given list of sentences.
"""

from sentence_transformers import SentenceTransformer, LoggingHandler
import numpy as np
import logging
from scipy import spatial

#### Just some code to print debug information to stdout
np.set_printoptions(threshold=100)

logging.basicConfig(format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO,
                    handlers=[LoggingHandler()])
#### /print debug information to stdout



# Load Sentence model (based on BERT) from URL
model = SentenceTransformer('bert-base-nli-mean-tokens')

# Embed a list of sentences
sentences = ['I love you',
             'I hate you']
sentence_embeddings = model.encode(sentences)
result = 1 - spatial.distance.cosine(sentence_embeddings[0],sentence_embeddings[1])
print(result)
# The result is a list of sentence embeddings as numpy arrays
for sentence, embedding in zip(sentences, sentence_embeddings):
    print("Sentence:", sentence)
    print("Embedding:", len(embedding))
    print("")
