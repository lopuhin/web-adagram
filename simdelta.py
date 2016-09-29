from collections import defaultdict

import adagram
import numpy as np

from senses import SensesHandler


class SimDeltaHandler(SensesHandler):
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
                ctx['similarity'] = np.dot(
                    vm.sense_vector(word, s1, normalized=True),
                    vm.sense_vector(word, s2, normalized=True))
                ctx['similar_pairs'] = self.find_similar_pairs(vm, word, s1, s2)
        self.render('templates/sim-delta.html', **ctx)

    def find_similar_pairs(self, vm, word, sense_1, sense_2):
        by_word = defaultdict(lambda : ([], []))
        for idx, sense in enumerate([sense_1, sense_2]):
            for w, s, sim in vm.sense_neighbors(
                    word, sense, max_neighbors=5000, min_closeness=0.35):
                by_word[w][idx].append((s, sim))
        pairs = [(word, s1, s2, min(sim1, sim2))
                 for word, (s1_sim, s2_sim) in by_word.items()
                 for s1, sim1 in s1_sim
                 for s2, sim2 in s2_sim
                 if s1 != s2]
        pairs.sort(key=lambda x: x[-1], reverse=True)
        return pairs[:30]
