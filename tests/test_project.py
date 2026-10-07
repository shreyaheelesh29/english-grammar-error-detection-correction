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


if __name__ == '__main__':
    unittest.main()
