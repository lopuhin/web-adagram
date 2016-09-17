import numpy as np
from numpy.linalg import norm
from tornado.web import RequestHandler

import adagram


class SimDeltaHandler(RequestHandler):
    def get(self):
        word = self.get_argument('word', None)
        s1 = self.get_argument('s1', '')
        s2 = self.get_argument('s2', '')
        if s1:
            s1 = int(s1)
        if s2:
            s2 = int(s2)
        sense_ids = {s1, s2}
        ctx = {'word': word, 'sense_1': s1, 'sense_2': s2, 'senses': None}
        if word is not None:
            vm = self.application \
                .settings['adagram_model']  # type: adagram.VectorModel
            try:
                sense_probs = vm.word_sense_probs(word)
            except KeyError:
                pass
            else:
                ctx['senses'] = self.senses(vm, word, sense_probs, sense_ids)
                word_id = vm.dictionary.word2id[word]
                ctx['freq'] = freq = vm.frequencies[word_id]
                ctx['ipm'] = freq / vm.frequencies.sum() * 1e6
                ctx['similar_pairs'] = self.find_similar_pairs(
                    vm, word, s1, s2)[:20]
        self.render('templates/sim-delta.html', **ctx)

    def senses(self, vm, word, sense_probs, sense_ids):
        senses = []
        for idx, prob in enumerate(sense_probs):
            neighbours = vm.sense_neighbors(word, idx, max_neighbors=5)
            senses.append({
                'idx': idx,
                'prob': prob,
                'highlight': idx in sense_ids,
                'neighbors': [
                    {'word': w, 'closeness': closeness}
                    for w, s_idx, closeness in neighbours],
            })
        senses.sort(key=lambda s: s['prob'], reverse=True)
        return senses

    def find_similar_pairs(self, vm, word, sense_1, sense_2):
        word_id = vm.dictionary.word2id[word]
        w_freq = vm.dictionary.frequencies[word_id]
        frequent_ids = [w_id for w_id, freq in
                        enumerate(vm.dictionary.frequencies)
                        if freq * 10 >= w_freq]
        frequent_words = [vm.dictionary.id2word[w_id] for w_id in frequent_ids]
        pairs = lambda lst: ((x, y) for x in lst for y in lst if x != y)
        sense_pairs = [
            (w, s1, s2, vm.In[w_id, s1] - vm.In[w_id, s2])
            for w, w_id in zip(frequent_words, frequent_ids)
            for s1, s2 in pairs(
                [s for s, prob in enumerate(vm.word_sense_probs(w))
                 if prob > 0.01])
            ]
        d_vec = vm.sense_vector(word, sense_1) - vm.sense_vector(word, sense_2)
        d_vec_norm = norm(d_vec)
        cos_sims = [(w, s1, s2, np.dot(d_vec, dv) / (norm(dv) * d_vec_norm))
                    for w, s1, s2, dv in sense_pairs]
        cos_sims.sort(key=lambda x: x[-1], reverse=True)
        return cos_sims
