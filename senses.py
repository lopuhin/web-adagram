import gzip
import hashlib
import re
from pathlib import Path
from urllib.parse import urlencode
from typing import List, Tuple

import adagram
import numpy as np
from pymystem3 import Mystem
from tornado.web import RequestHandler


class SensesHandler(RequestHandler):
    def get(self):
        word = self.get_argument('word', None)
        highlight = [int(sid) for sid in self.get_arguments('highlight')]
        ctx = {'word': word, 'senses': None}
        if word is not None:
            vm = self.application \
                .settings['adagram_model']  # type: adagram.VectorModel
            try:
                sense_probs = vm.word_sense_probs(word)
            except KeyError:
                pass
            else:
                ctx['senses'] = self.senses(vm, word, sense_probs, highlight)
                word_id = vm.dictionary.word2id[word]
                ctx['freq'] = freq = vm.frequencies[word_id]
                ctx['ipm'] = freq / vm.frequencies.sum() * 1e6
        self.render('templates/senses.html', **ctx)

    def senses(self, vm, word, sense_probs, highlight):
        senses = []
        collocates = dict(vm.word_sense_collocates(word, limit=5))
        contexts = self.get_contexts(word)
        context_probs = np.array(
            [vm.disambiguate(word, context_words(ctx)) for ctx in contexts])
        top_prob_indices = np.argsort(-context_probs, axis=0)
        for idx, prob in sense_probs:
            neighbours = vm.sense_neighbors(word, idx, max_neighbors=5)
            senses.append({
                'idx': idx,
                'prob': prob,
                'highlight': idx in highlight,
                'neighbors': [
                    {'word': w,
                     'link': '{}?{}'.format(
                         self.reverse_url('senses'),
                         urlencode({'word': w, 'highlight': s_idx})),
                     'closeness': closeness}
                    for w, s_idx, closeness in neighbours],
                'collocates': collocates.get(idx, []),
                'contexts': [join_context_punct(contexts[i])
                             for i in top_prob_indices[:5, idx]
                             if context_probs[i, idx] >= 0.9],
            })
        senses.sort(key=lambda s: s['prob'], reverse=True)
        return senses

    def get_contexts(self, word: str) -> List[str]:
        path = word_path(Path('contexts'), word)
        if path.exists():
            with gzip.open(str(path), 'rt') as f:
                contexts = []
                for line in f:
                    left, word, right = line.strip('\n ').split('\t')
                    contexts.append((left, word, right))
            return contexts
        else:
            return []


mystem = Mystem()
Ctx = Tuple[str, str, str],


def lemm_words(s: str) -> List[str]:
    return [w.lower() for w in mystem.lemmatize(s) if re.match('[\w\-]+$', w)]


def context_words(ctx: Ctx, window: int=10) -> List[str]:
    left, _, right = ctx
    return lemm_words(left)[-window:] + lemm_words(right)[:window]


def join_context_punct(ctx: Ctx) -> Ctx:
    left, word, right = ctx
    r = right[0]
    if right[1] == ' ' and not (r.isalpha() or r.isdigit() or r in '(-'):
        word = '{}{}'.format(word, r)
        right = right[2:]
    return left, word, right


def word_folder(root: Path, word: str) -> Path:
    return root.joinpath(hashlib.md5(word.encode('utf8')).hexdigest()[:2])


def word_path(root: Path, word: str) -> Path:
    return word_folder(root, word) / '{}.txt.gz'.format(word)
