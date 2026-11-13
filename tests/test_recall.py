import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import recall


class RecallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patch = patch.object(recall, 'DB', Path(self.temp.name) / 'test.db')
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def task(self, **changes):
        return {'title': 'Meet Maya, bring notes', 'kind': 'Task', 'category': 'Meeting', 'due_date': '2026-11-13 18:00', 'source': 'Meet Maya at six', **changes}

    def test_legacy_migration_preserves_tasks(self):
        with sqlite3.connect(recall.DB) as conn:
            conn.execute('CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL, category TEXT NOT NULL, due_date TEXT, source TEXT, done INTEGER DEFAULT 0)')
            conn.execute("INSERT INTO tasks VALUES (1, 'Old task', 'Other', '', 'Original', 0)")
        items = recall.list_items('personal')
        self.assertEqual(items[0]['title'], 'Old task')
        self.assertEqual(items[0]['kind'], 'Task')
        self.assertEqual(recall.list_items('someone-else'), [])

    def test_invalid_batch_is_not_partially_saved(self):
        with self.assertRaises(ValueError):
            recall.save_items('personal', [self.task(), self.task(due_date='tomorrow')])
        self.assertEqual(recall.list_items('personal'), [])

    def test_duplicates_and_owner_scoped_mutations(self):
        self.assertEqual(recall.save_items('personal', [self.task(), self.task()]), 1)
        item = recall.list_items('personal')[0]
        recall.update_item('someone-else', item['id'], delete=True)
        self.assertEqual(len(recall.list_items('personal')), 1)
        recall.update_item('personal', item['id'], done=True)
        self.assertEqual(recall.list_items('personal')[0]['done'], 1)

    def test_calendar_utc_escaping_folding_and_exclusions(self):
        result = recall.calendar_export([self.task(title='é' * 90 + ', test'), self.task(kind='Memory'), self.task(done=1), self.task(due_date='')])
        self.assertEqual(result.count('BEGIN:VEVENT'), 1)
        self.assertIn('DTSTART:20261114T000000Z', result)
        self.assertIn('\\, test', result)
        self.assertTrue(all(len(line.encode()) <= 75 for line in result.split('\r\n')))

    def test_memory_has_no_due_date_and_csv_neutralizes_formulas(self):
        recall.save_items('personal', [self.task(title='=HYPERLINK("bad")', kind='Memory')])
        items = recall.list_items('personal')
        self.assertEqual(items[0]['due_date'], '')
        self.assertIn("'=HYPERLINK", recall.csv_export(items))


if __name__ == '__main__':
    unittest.main()

class AssistantErrorTests(unittest.TestCase):
    def test_quota_failure_is_actionable_and_does_not_echo_sensitive_details(self):
        from google.genai.errors import ClientError
        error = ClientError(429, {'error': {'message': 'quota limit: 0 secret-key private-text', 'status': 'RESOURCE_EXHAUSTED'}})
        message = recall.assistant_error(error)
        self.assertIn('quota is zero', message)
        self.assertNotIn('secret-key', message)
        self.assertNotIn('private-text', message)

    def test_missing_model_and_invalid_key_are_distinct(self):
        from google.genai.errors import ClientError
        self.assertIn('model', recall.assistant_error(ClientError(404, {'error': {'message': 'not found'}})))
        self.assertIn('API key', recall.assistant_error(ClientError(400, {'error': {'message': 'API key not valid'}})))

class CalendarAndTakeawayTests(RecallTests):
    def test_reminder_persists_and_exports_as_alarm(self):
        recall.save_items('personal', [self.task(reminder=10, duration=60)])
        item = recall.list_items('personal')[0]
        self.assertEqual(item['reminder'], 10)
        result = recall.calendar_export([item])
        self.assertIn('BEGIN:VALARM\r\nTRIGGER:-PT10M', result)
        self.assertIn('DTEND:20261114T010000Z', result)
        recall.edit_item('personal', item['id'], {**item, 'title': 'Lunch with Emma', 'reminder': 0})
        edited = recall.list_items('personal')[0]
        self.assertEqual(edited['title'], 'Lunch with Emma')
        self.assertIn('TRIGGER:PT0M', recall.calendar_export([edited]))

    def test_date_only_exports_all_day_and_no_midnight_alarm(self):
        item = self.task(due_date='2026-11-15', reminder=30)
        result = recall.calendar_export([item])
        self.assertIn('DTSTART;VALUE=DATE:20261115', result)
        self.assertIn('DTEND;VALUE=DATE:20261116', result)
        self.assertNotIn('VALARM', result)

    def test_google_link_encodes_user_content(self):
        from urllib.parse import urlparse, parse_qs
        item = self.task(title='Lunch & coffee?')
        query = parse_qs(urlparse(recall.google_calendar_url(item)).query)
        self.assertEqual(query['text'], ['Lunch & coffee?'])
        self.assertEqual(query['dates'], ['20261114T000000Z/20261114T003000Z'])

    def test_pdf_is_a_printable_document_with_untrusted_markup(self):
        result = recall.pdf_card([self.task(title='Lunch <Emma> & friends', source='Bring <notes>')])
        self.assertTrue(result.startswith(b'%PDF-'))
        self.assertIn(b'%%EOF', result)
        self.assertGreater(len(result), 1000)

    def test_edit_cannot_change_another_owner(self):
        recall.save_items('personal', [self.task()])
        item = recall.list_items('personal')[0]
        recall.edit_item('other', item['id'], self.task(title='Wrong'))
        self.assertEqual(recall.list_items('personal')[0]['title'], item['title'])
