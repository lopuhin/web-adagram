#!/usr/bin/env python
import argparse
import logging
from pathlib import Path
from urllib.parse import urlencode

import tornado.ioloop
from tornado.web import Application, RequestHandler, URLSpec
import adagram


logging.basicConfig(
    format='[%(levelname)s] %(asctime)s %(message)s', level=logging.INFO)
ROOT = Path(__file__).parent
STATIC_ROOT = ROOT / 'static'


class MainHandler(RequestHandler):
    def get(self):
        word = self.get_argument('word', None)
        sense_idx = self.get_argument('sense', None)
        if sense_idx is not None:
            sense_idx = int(sense_idx)
        senses = []
        if word is not None:
            vm = self.application\
                .settings['adagram_model']  # type: adagram.VectorModel
            try:
                sense_probs = vm.word_sense_probs(word)
            except KeyError:
                pass
            else:
                for idx, prob in enumerate(sense_probs):
                    neighbours = vm.sense_neighbors(word, idx, max_neighbors=5)
                    senses.append({
                        'idx': idx,
                        'prob': prob,
                        'highlight': idx == sense_idx,
                        'neighbors': [
                            {'word': w,
                             'link': '{}?{}'.format(
                                 self.reverse_url('main'),
                                 urlencode({'word': w, 'sense': s_idx})),
                             'closeness': closeness}
                            for w, s_idx, closeness in neighbours],
                    })
                senses.sort(key=lambda s: s['prob'], reverse=True)
        self.render('templates/main.html', word=word, senses=senses)


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
