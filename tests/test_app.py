import unittest
import os
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class AppTests(unittest.TestCase):
    def test_conversation_review_takeaway_and_visitor_reset(self):
        env = patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key'})
        env.start()
        self.addCleanup(env.stop)
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
        self.assertFalse(app.exception)
        app.text_area[0].set_value('Meet Maya today at six')
        draft = {'title': 'Meet Maya', 'kind': 'Task', 'category': 'Meeting', 'due_date': '2026-11-13 18:00', 'source': 'Meet Maya today at six'}
        with patch('recall.converse', return_value=('I found your plan. Please review it.', [draft])):
            next(b for b in app.button if b.label == 'Help me remember').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state['messages']), 2)
        self.assertEqual(app.session_state['page'], 'Review')
        next(b for b in app.button if b.label == 'Save reviewed items').click().run()
        self.assertEqual(len(app.session_state['visitor_items']), 1)
        app.segmented_control(key='page').set_value('My recall').run()
        next(c for c in app.checkbox if c.label == 'Meet Maya').check().run()
        self.assertEqual(app.session_state['visitor_items'][0]['done'], 1)
        self.assertEqual(next(m for m in app.metric if m.label == 'Stars earned').value, '⭐ 1')
        app.checkbox(key='show_done').check().run()
        next(c for c in app.checkbox if c.label == 'Meet Maya').uncheck().run()
        self.assertEqual(next(m for m in app.metric if m.label == 'Stars earned').value, '⭐ 0')
        app.segmented_control(key='page').set_value('Take away').run()
        self.assertFalse(app.exception)
        app.session_state['retry_text'] = 'Previous visitor private text'
        app.button(key='next_visitor').click().run()
        self.assertEqual(app.session_state['visitor_items'], [])
        self.assertEqual(app.session_state['messages'], [])
        self.assertNotIn('retry_text', app.session_state)
        self.assertFalse(any(x.key == 'api_key' for x in app.text_input))
        self.assertFalse(app.exception)


if __name__ == '__main__':
    unittest.main()

class ExpoTests(unittest.TestCase):
    def test_live_date_picker_edit_and_personal_hidden(self):
        env = patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key'})
        env.start()
        self.addCleanup(env.stop)
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
        self.assertFalse(app.exception)
        self.assertFalse(any(x.key == 'workspace' for x in app.radio))
        self.assertFalse(any(x.key == 'offline' for x in app.toggle))
        app.text_area[0].set_value('Get lunch')
        draft = {'title': 'Get lunch', 'kind': 'Task', 'category': 'Personal', 'due_date': '', 'source': 'Get lunch'}
        with patch('recall.converse', return_value=('Review your lunch plan.', [draft])):
            next(b for b in app.button if b.label == 'Help me remember').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.session_state['drafts']), 1)
            next(x for x in app.selectbox if x.key.endswith('_0_reminder')).select('10 minutes before')
            # Lunch needs a chosen date AND time before a timed reminder can be saved.
            from datetime import date, time
            next(x for x in app.date_input if x.key.endswith('_0_date')).set_value(date(2026, 11, 15))
            next(x for x in app.time_input if x.key.endswith('_0_time')).set_value(time(12, 0))
            next(b for b in app.button if b.label == 'Save reviewed items').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['visitor_items'][0]['reminder'], 10)
            self.assertEqual(app.session_state['visitor_items'][0]['due_date'], '2026-11-15 12:00')
            app.segmented_control(key='page').set_value('My recall').run()
            next(x for x in app.text_input if x.label == 'Title').set_value('Lunch with Emma')
            next(b for b in app.button if b.label == 'Save changes').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['visitor_items'][0]['title'], 'Lunch with Emma')
            app.segmented_control(key='page').set_value('Take away').run()
            self.assertFalse(app.exception)
