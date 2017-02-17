#!/usr/bin/env python
import argparse
from datetime import datetime
import gzip
import hashlib
import random
from pathlib import Path
from typing import List

from adagram import VectorModel
from pymystem3 import Mystem


mystem = Mystem()


def main():
    parser = argparse.ArgumentParser()
    arg = parser.add_argument
    arg('model', help='Take words from this model')
    arg('corpus', type=Path, help='shuffled corpus')
    arg('output', type=Path)
    arg('--window', type=int, default=25,
        help='includes punctuation and spaces')
    arg('--max', type=int, default=1000, help='contexts per word')
    args = parser.parse_args()

    vm = VectorModel.load(args.model)
    words = list(vm.dictionary.id2word)
    del vm
    popular_words = set(words[:500])
    words = set(words)

    contexts_by_w = {w: [] for w in words}
    with args.corpus.open('rt') as f:
        for w, ctx in line_contexts_iter(
                f, words, window_size=args.window):
            contexts = contexts_by_w[w]
            contexts.append(ctx)
            max_contexts = args.max * (50 if w in popular_words else 2)
            if len(contexts) >= max_contexts:
                del contexts_by_w[w]
                words.remove(w)
                write_contexts(w, contexts, args.output, args.max)

    for w, contexts in contexts_by_w:
        write_contexts(w, contexts, args.output, args.max)


def write_contexts(w, contexts: List[str], output: Path, max_contexts: int):
    if len(contexts) > max_contexts:
        contexts = random.sample(contexts, max_contexts)
    folder = word_folder(output, w)
    folder.mkdir(exist_ok=True)
    with gzip.open(str(folder / '{}.txt.gz'.format(w)), 'wt') as f:
        for ctx in contexts:
            f.write(ctx)
            f.write('\n')


def word_folder(root: Path, word: str) -> Path:
    return root.joinpath(hashlib.md5(word.encode('utf8')).hexdigest()[:2])


def line_contexts_iter(f, words, window_size):
    for i, line in enumerate(f):
        if i % 10000 == 0:
            print('{} {:,}'.format(datetime.now(), i))
        chunk = mystem.analyze(line)
        for idx, a in enumerate(chunk):
            analysis = a.get('analysis')
            if analysis:
                lemma = analysis[0]['lex']
                if lemma in words:
                    before = _join(chunk[max(0, idx - window_size) : idx])
                    after = _join(chunk[idx + 1 : idx + window_size + 1])
                    yield lemma, '\t'.join([before, a['text'], after])


def _join(analyzed):
    return ''.join(t['text'] for t in analyzed).strip()


if __name__ == '__main__':
    main()
