from args import args
from cws import ChineseSegmentor

if __name__ == '__main__':
    cws_obj = ChineseSegmentor(args.model_path, args.vocab_file, None, args.EMBEDDING_DIM, args.HIDDEN_DIM)
    if args.test_has_label:
        cws_obj.test_file_with_label(args.test_file, args.test_output_file)
    else:
        cws_obj.test_file_without_label(args.test_file, args.test_output_file)
    print(cws_obj.seg('你知道 jay z吗',['大大罗','罗吗大']))