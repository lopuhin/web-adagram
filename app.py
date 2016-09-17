#!/usr/bin/env python
import argparse
import logging
from pathlib import Path
from urllib.parse import urlencode

import tornado.ioloop
from tornado.web import Application, RequestHandler, URLSpec
import adagram

from simdelta import SimDeltaHandler


logging.basicConfig(
    format='[%(levelname)s] %(asctime)s %(message)s', level=logging.INFO)
ROOT = Path(__file__).parent
STATIC_ROOT = ROOT / 'static'


class MainHandler(RequestHandler):
    def get(self):
        word = self.get_argument('word', None)
        highlight = [int(sid) for sid in self.get_arguments('highlight')]
        ctx = {'word': word, 'senses': None}
        if word is not None:
            vm = self.application\
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
        self.render('templates/main.html', **ctx)

    def senses(self, vm, word, sense_probs, highlight):
        senses = []
        for idx, prob in enumerate(sense_probs):
            neighbours = vm.sense_neighbors(word, idx, max_neighbors=5)
            senses.append({
                'idx': idx,
                'prob': prob,
                'highlight': idx in highlight,
                'neighbors': [
                    {'word': w,
                     'link': '{}?{}'.format(
                         self.reverse_url('main'),
                         urlencode({'word': w, 'highlight': s_idx})),
                     'closeness': closeness}
                    for w, s_idx, closeness in neighbours],
            })
        senses.sort(key=lambda s: s['prob'], reverse=True)
        return senses


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('model')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    logging.info('Loading adagram model')
    adagram_model = adagram.VectorModel.load(args.model)
    app = Application(
        [URLSpec(r'/', MainHandler, name='main'),
         URLSpec(r'/sim-delta/', SimDeltaHandler, name='sim-delta'),
        ],
        debug=args.debug,
        static_prefix='/static/',
        static_path=str(STATIC_ROOT),
        adagram_model=adagram_model,
    )
    logging.info('Listening on port {}'.format(args.port))
    app.listen(args.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
