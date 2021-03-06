#!/usr/bin/env python
import argparse
import logging
from pathlib import Path

import adagram
import tornado.ioloop
from tornado.web import Application, RequestHandler, URLSpec

from senses import SensesHandler, mystem
from simdelta import SimDeltaHandler


logging.basicConfig(
    format='[%(levelname)s] %(asctime)s %(message)s', level=logging.INFO)
ROOT = Path(__file__).parent
STATIC_ROOT = ROOT / 'static'


class AboutHandler(RequestHandler):
    def get(self):
        self.render('templates/about.html')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('model')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--host', default='127.0.0.1')
    args = parser.parse_args()
    mystem.start()
    logging.info('Loading adagram model')
    adagram_model = adagram.VectorModel.load(args.model)
    app = Application(
        [URLSpec(r'/', SensesHandler, name='senses'),
         URLSpec(r'/sim-delta', SimDeltaHandler, name='sim-delta'),
         URLSpec(r'/about', AboutHandler, name='about'),
        ],
        debug=args.debug,
        static_prefix='/static/',
        static_path=str(STATIC_ROOT),
        adagram_model=adagram_model,
    )
    logging.info('Listening on port {}'.format(args.port))
    app.listen(args.port, args.host)
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
