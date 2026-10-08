import unittest
from types import SimpleNamespace
from unittest.mock import patch
from app import app
from nlp.cyk_parser import parse
from nlp.grammar_rules import run_rules
from nlp.language_engine import normalize_matches
from nlp.checking import check_document


class GrammarProjectTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_subject_verb_and_correction(self):
        data = self.client.post('/check', json={'text': 'She go to college.'}).get_json()
        self.assertEqual(data['corrected_text'], 'She goes to college.')
        self.assertEqual(data['errors'][0]['error_type'], 'Subject-Verb Agreement')
        self.assertIn('grammar_score', data)

    def test_third_person_regular_verb(self):
        data = self.client.post('/check', json={'text': 'he dance with her'}).get_json()
        self.assertEqual(data['corrected_text'], 'He dances with her.')

    def test_dependency_rule_handles_unlisted_verb(self):
        from nlp.grammar_rules import detect_subject_verb
        tags = [
            {'token': 'The', 'pos': 'DET', 'tag': 'DT', 'lemma': 'the', 'morphology': '', 'idx': 0, 'dep': 'det', 'token_i': 0, 'head_i': 1},
            {'token': 'researcher', 'pos': 'NOUN', 'tag': 'NN', 'lemma': 'researcher', 'morphology': 'Number=Sing', 'idx': 4, 'dep': 'nsubj', 'token_i': 1, 'head_i': 2},
            {'token': 'analyze', 'pos': 'VERB', 'tag': 'VB', 'lemma': 'analyze', 'morphology': 'VerbForm=Fin|Tense=Pres', 'idx': 15, 'dep': 'ROOT', 'token_i': 2, 'head_i': 2},
        ]
        errors = detect_subject_verb('The researcher analyze', tags)
        self.assertEqual([(e['original'], e['corrected']) for e in errors], [('analyze', 'analyzes')])

    def test_language_engine_matches_keep_document_offsets(self):
        text = 'The dog chase the cats.'
        # language_tool_python.Match exposes snake_case fields.
        match = SimpleNamespace(offset=8, error_length=5, replacements=['chases'],
                                category='GRAMMAR', rule_id='TEST_RULE',
                                message='Check subject–verb agreement.')
        findings = normalize_matches([match], text)
        self.assertEqual(len(findings), 1)
        self.assertEqual((findings[0]['original'], findings[0]['corrected']), ('chase', 'chases'))
        self.assertEqual(text[findings[0]['start']:findings[0]['end']], findings[0]['original'])
        self.assertEqual(findings[0]['rule_id'], 'TEST_RULE')

    def test_language_engine_accepts_api_style_match_fields(self):
        text = 'They was ready.'
        findings = normalize_matches([{
            'offset': 5, 'errorLength': 3, 'replacements': [{'value': 'were'}],
            'category': {'name': 'GRAMMAR'}, 'ruleId': 'TEST_API_RULE',
            'message': 'Check agreement.',
        }], text)
        self.assertEqual((findings[0]['original'], findings[0]['corrected']), ('was', 'were'))
        self.assertEqual(findings[0]['rule_id'], 'TEST_API_RULE')

    def test_shared_document_checker_preserves_engine_offsets_across_sentences(self):
        text = 'First sentence. The dog chase cats.'
        finding = {
            'start': text.index('chase'), 'end': text.index('chase') + 5,
            'original': 'chase', 'corrected': 'chases',
            'sentence_index': 0,
        }
        with patch('nlp.checking.check_with_language_tool', return_value=([finding], 'LanguageTool local engine')):
            errors, engine = check_document(text, ['First sentence.', 'The dog chase cats.'], [[], []])
        self.assertEqual(engine, 'LanguageTool local engine')
        self.assertEqual(errors[0]['sentence_index'], 1)

    def test_style_suggestion_control_toggles_optional_rewrites(self):
        text = 'We went to the baseball game, and after that, we stopped to get something to eat.'
        with patch('app.check_document', return_value=([], 'LanguageTool local engine')):
            enabled = self.client.post('/check', json={
                'text': text, 'include_style_suggestions': True,
            }).get_json()
            disabled = self.client.post('/check', json={
                'text': text, 'include_style_suggestions': False,
            }).get_json()
        self.assertTrue(enabled['writing_alternatives'])
        self.assertEqual(disabled['writing_alternatives'], [])

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

    def test_past_tense_rules_cover_more_regular_and_copula_verbs(self):
        for sentence, expected in [
            ('Yesterday, we borrow books.', 'Yesterday, we borrowed books.'),
            ('She is happy yesterday.', 'She was happy yesterday.'),
            ('In 2020, he goes to college.', 'In 2020, he went to college.'),
            ('They finished the work two days ago.', 'They finished the work two days ago.'),
        ]:
            errors = run_rules(sentence)
            corrected = sentence
            for error in sorted(errors, key=lambda item: item['start'], reverse=True):
                corrected = corrected[:error['start']] + error['corrected'] + corrected[error['end']:]
            self.assertEqual(corrected, expected, sentence)

        fallback_sentence = 'Yesterday, I goes to the library.'
        fallback_errors = run_rules(fallback_sentence)
        fallback_corrected = fallback_sentence
        for error in sorted(fallback_errors, key=lambda item: item['start'], reverse=True):
            fallback_corrected = (fallback_corrected[:error['start']] + error['corrected']
                                  + fallback_corrected[error['end']:])
        self.assertEqual(fallback_corrected, 'Yesterday, I went to the library.')

    def test_explicit_past_rule_overrides_conflicting_language_tool_suggestion(self):
        text = 'Yesterday, he goes to the library.'
        start = text.index('goes')
        language_tool_finding = {
            'start': start, 'end': start + len('goes'), 'original': 'goes',
            'corrected': 'goes', 'error_type': 'Grammar', 'sentence_index': 0,
        }
        with patch('nlp.checking.check_with_language_tool',
                   return_value=([language_tool_finding], 'LanguageTool local engine')):
            errors, engine = check_document(text, [text], [[]])
        self.assertEqual(engine, 'LanguageTool local engine + explicit past-time rules')
        corrected = text
        for error in sorted(errors, key=lambda item: item['start'], reverse=True):
            corrected = corrected[:error['start']] + error['corrected'] + corrected[error['end']:]
        self.assertEqual(corrected, 'Yesterday, he went to the library.')
        self.assertTrue(any(error['error_type'] == 'Tense Error' for error in errors))

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
