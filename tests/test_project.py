import unittest
from app import app
from nlp.cyk_parser import parse
from nlp.grammar_rules import run_rules


class GrammarProjectTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_subject_verb_and_correction(self):
        data = self.client.post('/check', json={'text': 'She go to college.'}).get_json()
        self.assertEqual(data['corrected_text'], 'She goes to college.')
        self.assertEqual(data['errors'][0]['error_type'], 'Subject-Verb Agreement')
        self.assertIn('grammar_score', data)

    def test_empty_and_oversize_requests(self):
        self.assertEqual(self.client.post('/check', json={'text': '  '}).status_code, 400)
        self.assertEqual(self.client.post('/check', json={'text': 'x' * 20001}).status_code, 413)

    def test_cyk_supported_and_outside_grammar(self):
        self.assertTrue(parse('She reads the book')['accepted'])
        self.assertFalse(parse('blue quickly')['accepted'])

    def test_missing_final_punctuation(self):
        errors = run_rules('She goes home')
        self.assertTrue(any(e['error_type'] == 'Punctuation' for e in errors))

    def test_past_time_cue_corrects_common_irregular_verbs(self):
        text = 'Yesterday, me and my friend goes to the store, but the shop keeper say we was late.'
        data = self.client.post('/check', json={'text': text}).get_json()
        self.assertEqual(
            data['corrected_text'],
            'Yesterday, my friend and I went to the store, but the shop keeper said we were late.'
        )
        tense_corrections = [e['corrected'] for e in data['errors'] if e['error_type'] == 'Tense Error']
        self.assertEqual(tense_corrections, ['went', 'said'])

    def test_past_tense_rule_preserves_infinitive_after_to(self):
        errors = run_rules('Yesterday, I wanted to buy a book.')
        self.assertFalse(any(e['error_type'] == 'Tense Error' and e['original'] == 'buy' for e in errors))

    def test_reported_sentence_catches_common_errors(self):
        text = ('Yesterday, me and my friend goes to the store for buy some apple. '
                'There is three dog running fastly on the street, and we was shocking very much. '
                'I should of told him to not touch the animal, but the food was already ready '
                'on the table when we gets back home.')
        data = self.client.post('/check', json={'text': text}).get_json()
        self.assertEqual(
            data['corrected_text'],
            ('Yesterday, my friend and I went to the store to buy some apples. '
             'There were three dogs running fast on the street, and we were very shocked. '
             'I should have told him to not touch the animal, but the food was already ready '
             'on the table when we got back home.')
        )


if __name__ == '__main__':
    unittest.main()
