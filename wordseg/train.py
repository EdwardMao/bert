import io
import logging
import numpy as np
import os
import pickle
import queue
import random
import shutil
import sys
import utils
import torch
import torch.utils.data as data
import tqdm

from args import args
from json import dumps
from lstm_crf import BiLSTMCRF
from torch import optim
from tensorboardX import SummaryWriter

global train_logger


class CheckpointSaver:
    """Class to save and load model checkpoints.

    Save the best checkpoints as measured by a metric value passed into the
    `save` method. Overwrite checkpoints with better checkpoints once
    `max_checkpoints` have been saved.

    Args:
        save_dir (str): Directory to save checkpoints.
        max_checkpoints (int): Maximum number of checkpoints to keep before
            overwriting old ones.
        metric_name (str): Name of metric used to determine best model.
        maximize_metric (bool): If true, best checkpoint is that which maximizes
            the metric value passed in via `save`. Otherwise, best checkpoint
            minimizes the metric.
        log (logging.Logger): Optional logger for printing information.
    """

    def __init__(self, save_dir, max_checkpoints, metric_name, maximize_metric=False, log=None):
        super(CheckpointSaver, self).__init__()

        self.save_dir = save_dir
        self.max_checkpoints = max_checkpoints
        self.metric_name = metric_name
        self.maximize_metric = maximize_metric
        self.best_val = None
        self.ckpt_paths = queue.PriorityQueue()
        self.log = log
        self._print('Saver will {}imize {}...'.format('max' if maximize_metric else 'min', metric_name))

    def is_best(self, metric_val):
        """Check whether `metric_val` is the best seen so far.

        Args:
            metric_val (float): Metric value to compare to prior checkpoints.
        """
        if metric_val is None:
            # No metric reported
            return False

        if self.best_val is None:
            # No checkpoint saved yet
            return True

        return ((self.maximize_metric and self.best_val < metric_val)
                or (not self.maximize_metric and self.best_val > metric_val))

    def _print(self, message):
        """Print a message if logging is enabled."""
        if self.log is not None:
            self.log.info(message)

    def save(self, step, model, metric_val, device, path=None):
        """Save model parameters to disk.

        Args:
            step (int): Total number of examples seen during training so far.
            model (torch.nn.DataParallel): Model to save.
            metric_val (float): Determines whether checkpoint is best so far.
            device (torch.device): Device where model resides.
        """
        ckpt_dict = {
            'model_name': model.__class__.__name__,
            'model_state': model.cpu().state_dict(),
            'step': step
        }
        model.to(device)

        checkpoint_path = os.path.join(self.save_dir,
                                       'step_{}.pth.tar'.format(step))
        torch.save(ckpt_dict, checkpoint_path)
        self._print('Saved checkpoint: {}'.format(checkpoint_path))

        if self.is_best(metric_val):
            # Save the best model
            self.best_val = metric_val
            if path:
                best_path = path
            else:
                best_path = os.path.join(self.save_dir, 'best.pth.tar')
            if os.path.exists(best_path):
                os.remove(best_path)
            shutil.copy(checkpoint_path, best_path)
            self._print('New best checkpoint at step {}...'.format(step))

        # Add checkpoint path to priority queue (lowest priority removed first)
        if self.maximize_metric:
            priority_order = metric_val
        else:
            priority_order = -metric_val

        self.ckpt_paths.put((priority_order, checkpoint_path))

        # Remove a checkpoint if more than max_checkpoints have been saved
        if self.ckpt_paths.qsize() > self.max_checkpoints:
            _, worst_ckpt = self.ckpt_paths.get()
            try:
                os.remove(worst_ckpt)
                self._print('Removed checkpoint: {}'.format(worst_ckpt))
            except OSError:
                # Avoid crashing if checkpoint has been removed or protected
                pass


def set_random():

    train_logger.info('Using random seed {}...'.format(args.seed))
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    return


def load_data():

    from pathlib import Path
    global train_logger

    vocab_file = args.vocab_file
    word_to_ix = {}
    if os.path.exists(vocab_file):
        try:
            with io.open(vocab_file, 'rb') as f:
                word_to_ix = pickle.load(f)
        except Exception:
            log_str = "Error in loading vocab file [%s] !" % vocab_file
            train_logger.error(log_str)
            sys.stderr.write(log_str + "\n")
            sys.exit()

    train_file = args.train_file
    if len(set(Path(train_file).suffixes).intersection(set([".tsv", ".txt"]))) > 0:
        train_data, word_to_ix = utils.load_data_with_label(train_file, word_to_ix, True)
    elif len(set(Path(train_file).suffixes).intersection(set([".p", ".pickle"]))) > 0:
        with io.open(train_file, 'rb') as f:
            train_data = pickle.load(f)
    else:
        log_str = "Train file [%s] is not supported!" % train_file
        train_logger.error(log_str)
        sys.stderr.write(log_str + "\n")
        sys.exit()

    dev_file = args.dev_file
    if len(set(Path(train_file).suffixes).intersection(set([".tsv", ".txt"]))) > 0:
        dev_data, word_to_ix = utils.load_data_with_label(dev_file, word_to_ix, False)
    elif len(set(Path(train_file).suffixes).intersection(set([".p", ".pickle"]))) > 0:
        with io.open(dev_file, 'rb') as f:
            dev_data = pickle.load(f)
    else:
        log_str = "Dev file [%s] is not supported!" % dev_file
        train_logger.error(log_str)
        sys.stderr.write(log_str + "\n")
        sys.exit()

    return train_data, dev_data, word_to_ix


def evaluate(model, device, eval_data):

    model.eval()
    F1 = 0.0
    count = 0
    with torch.no_grad():
        for sentence, label, mask in eval_data:
            masks = mask.to(device)

            sen = sentence.to(device)
            temp_pred = model(sen, masks)[1]
            temp_gold = label
            for i in range(len(label)):
                count += 1
                temppred = torch.tensor(temp_pred[i], dtype=torch.long)
                tempgold = temp_gold[i][:torch.sum(masks[i] > 0).item()]
                F1 += utils.compute_f1(tempgold, temppred)
    F1 = F1 / count
    model.train()

    return F1


def get_save_dir(base_dir, name, training, id_max=100):
    """Get a unique save directory by appending the smallest positive integer
    `id < id_max` that is not already taken (i.e., no dir exists with that id).

    Args:
        base_dir (str): Base directory in which to make save directories.
        name (str): Name to identify this training run. Need not be unique.
        training (bool): Save dir. is for training (determines subdirectory).
        id_max (int): Maximum ID number before raising an exception.

    Returns:
        save_dir (str): Path to a new directory with a unique name.
    """
    for uid in range(1, id_max):
        subdir = 'train' if training else 'test'
        save_dir = os.path.join(base_dir, subdir, '{}-{:02d}'.format(name, uid))
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            return save_dir

    raise RuntimeError('Too many save directories created with the same name. \
                       Delete old save directories or use another name.')


def get_logger(log_dir, name):
    """Get a `logging.Logger` instance that prints to the console
    and an auxiliary file.

    Args:
        log_dir (str): Directory in which to create the log file.
        name (str): Name to identify the logs.

    Returns:
        logger (logging.Logger): Logger instance for logging events.
    """

    class StreamHandlerWithTQDM(logging.Handler):
        """Let `logging` print without breaking `tqdm` progress bars.

        See Also:
            > https://stackoverflow.com/questions/38543506
        """

        def emit(self, record):
            try:
                msg = self.format(record)
                tqdm.tqdm.write(msg)
                self.flush()
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                self.handleError(record)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Log everything (i.e., DEBUG level and above) to a file
    log_path = os.path.join(log_dir, 'log.txt')
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.DEBUG)

    # Log everything except DEBUG level (i.e., INFO level and above) to console
    console_handler = StreamHandlerWithTQDM()
    console_handler.setLevel(logging.INFO)

    # Create format for the logs
    file_formatter = logging.Formatter('[%(asctime)s] %(message)s',
                                       datefmt='%m.%d.%y %H:%M:%S')
    file_handler.setFormatter(file_formatter)
    console_formatter = logging.Formatter('[%(asctime)s] %(message)s',
                                          datefmt='%m.%d.%y %H:%M:%S')
    console_handler.setFormatter(console_formatter)

    # add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


if __name__ == '__main__':

    global train_logger
    args.save_dir = get_save_dir(args.save_dir,
                                 args.name +
                                 '_lr' + f'{args.lr}' +
                                 '_epochs' + f'{args.num_epochs}' +
                                 '_hidden' + f'{args.HIDDEN_DIM}' +
                                 '_embed' + f'{args.EMBEDDING_DIM}' +
                                 '_batch' + f'{args.batch_size}',
                                 training=True)
    train_logger = get_logger(args.save_dir, args.name)
    train_logger.info('Args: {}'.format(dumps(vars(args), indent=4, sort_keys=True)))



    tbx = SummaryWriter(args.save_dir)
    device, args.gpu_ids = utils.get_available_devices()
    args.batch_size *= 1  # max(1, len(args.gpu_ids))

    set_random()

    train_logger.info('Loading data from file')
    train_data, dev_data, word_to_ix = load_data()

    # print(dev_data)
    train_logger.info('Transferring data into dataset')
    train_dataset = utils.Dataset(train_data)
    train_loader = data.DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True,
                                   collate_fn=utils.collate_fn_with_label)
    dev_dataset = utils.Dataset(dev_data)
    dev_loader = data.DataLoader(dev_dataset, batch_size=args.batch_size, shuffle=False,
                                 collate_fn=utils.collate_fn_with_label)

    # model
    train_logger.info('Building model...')
    model = BiLSTMCRF(device, utils.tag_to_ix, len(word_to_ix) + 2, args.EMBEDDING_DIM, args.HIDDEN_DIM)
    if args.load_path:
        train_logger.info('Loading checkpoint from {}...'.format(args.load_path))
        model, step = utils.load_model(model, args.load_path, args.gpu_ids)
    else:
        step = 0

    model = model.to(device)
    model.train()

    # Saver
    saver = CheckpointSaver(args.save_dir,
                            max_checkpoints=5,
                            metric_name='F1',
                            maximize_metric=True,
                            log=train_logger)

    optimizer = optim.Adam(model.parameters(), lr=args.lr)
    scheduler = optim.lr_scheduler.LambdaLR(optimizer, lambda epoch: 0.9 ** epoch)

    # training
    train_logger.info('Training...')
    steps_till_eval = args.eval_steps
    temp_epoch = step // len(train_dataset)
    for epoch in range(args.num_epochs - temp_epoch):
        train_logger.info(f'Starting epoch {epoch}...')
        scheduler.step()
        with torch.enable_grad(), tqdm.tqdm(total=len(train_loader.dataset)) as progress_bar:
            for sentence, tags, mask in train_loader:
                batch_size = sentence.size(0)

                masks = mask.to(device)
                model.zero_grad()
                sen = sentence.to(device)
                targets = tags.to(device)

                loss = model.loss(sen, targets, masks)
                loss.backward()
                optimizer.step()

                # log information
                step += batch_size  # batch_size
                progress_bar.update(batch_size)
                tbx.add_scalar('train/loss', loss.item(), step)

                # evaluate
                steps_till_eval -= batch_size
                if steps_till_eval <= 0 and args.dev:
                    if epoch == args.num_epochs - temp_epoch - 1:
                        steps_till_eval = args.eval_steps // 10
                    else:
                        steps_till_eval = args.eval_steps
                    train_logger.info('Evaluate at step {}...'.format(step))
                    result = evaluate(model, device, dev_loader)
                    saver.save(step, model, result, device, args.model_path)
                    train_logger.info(f'Dev F1: {result}')

                    train_logger.info(f'Loss: {loss.item()}')
                    tbx.add_scalar('dev/F1', result, step)

    # ckpt_dict = {
    #     'model_name': model.__class__.__name__,
    #     'model_state': model.cpu().state_dict(),
    #     'step': step
    # }
    # model.to(device)
    # torch.save(ckpt_dict, args.model_path)

    train_logger.info('Evaluate at step {}...'.format(step))
    result = evaluate(model, device, dev_loader)
    saver.save(step, model, result, device, args.model_path)
    train_logger.info(f'Dev F1: {result}')
    train_logger.info(f'Loss: {loss.item()}')
    tbx.add_scalar('dev/F1', result, step)

    with open(args.vocab_file, 'wb') as output:
        pickle.dump(word_to_ix, output)


