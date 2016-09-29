from urllib.parse import urlencode

import adagram
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
            })
        senses.sort(key=lambda s: s['prob'], reverse=True)
        return senses


