
from online.cws import ChineseSegmentor

cs = ChineseSegmentor("./best.pth.tar", "./word_to_ix.p", "./dictionary.utf8")
words = cs.seg("孙悟空着肚子去上海洋人防工程的课")
print(words)