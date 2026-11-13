import os
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import streamlit as st
from dotenv import dotenv_values

from recall import (CATEGORIES, ZONE, action_card, assistant_error, calendar_export, converse,
                    csv_export, list_items, save_items, update_item, validate_date,
                    REMINDERS, normalize_item, edit_item, google_calendar_url, pdf_card)
from expo import SAMPLES

st.set_page_config(page_title='CampusRecall', page_icon=':material/psychology:', layout='wide')

DEFAULTS = {'messages': [], 'drafts': [], 'revision': 0, 'visitor_items': [], 'visitor_id': str(uuid4()), 'notice': '', 'page': 'Capture'}
for name, value in DEFAULTS.items():
    if name not in st.session_state:
        st.session_state[name] = value


def reset_conversation():
    st.session_state.messages = []
    st.session_state.drafts = []
    st.session_state.revision += 1
    st.session_state.pop('retry_text', None)


def get_items():
    return st.session_state.visitor_items if visitor else list_items('personal')


def save_selected(items):
    if not visitor:
        return save_items('personal', items)
    existing = {(x['title'].casefold(), x['kind'], x['due_date']) for x in st.session_state.visitor_items}
    count = 0
    items = [normalize_item(item) for item in items]
    for item in items:
        identity = (item['title'].casefold(), item['kind'], item['due_date'])
        if identity not in existing:
            st.session_state.visitor_items.append({**item, 'id': str(uuid4()), 'done': 0})
            existing.add(identity)
            count += 1
    return count


def item_fields(item, prefix):
    title = st.text_input('Title', value=item['title'], key=f'{prefix}_title')
    a, b = st.columns(2)
    kind = a.selectbox('Type', ['Task', 'Memory'], index=int(item['kind'] == 'Memory'), key=f'{prefix}_kind')
    category = b.selectbox('Category', CATEGORIES, index=CATEGORIES.index(item['category']), key=f'{prefix}_cat')
    value = item.get('due_date', '')
    try:
        parsed = datetime.fromisoformat(value) if value else None
    except ValueError:
        parsed = None
    with st.expander('Date & reminder', expanded=bool(value)):
        a, b = st.columns(2)
        day = a.date_input('Date', value=parsed.date() if parsed else None, key=f'{prefix}_date', format='MM/DD/YYYY')
        hour = b.time_input('Time', value=parsed.time() if parsed and len(value) > 10 else None, key=f'{prefix}_time', step=60)
        a, b = st.columns(2)
        reminders = list(REMINDERS)
        reminder_value = item.get('reminder', -1)
        reminder = a.selectbox('Remind me', reminders, index=list(REMINDERS.values()).index(reminder_value) if reminder_value in REMINDERS.values() else 0, key=f'{prefix}_reminder')
        durations = [15, 30, 60, 90, 120]
        duration = b.selectbox('Event length', durations, index=durations.index(item.get('duration', 30)) if item.get('duration', 30) in durations else 1, format_func=lambda minutes: f'{minutes} min', key=f'{prefix}_duration')
        st.caption('Chicago time · No time = all day · Memories don’t need dates.')
    due = str(day) if day else ''
    if day and hour:
        due = f'{day} {hour:%H:%M}'
    # Keep invalid combinations visible to validation instead of silently losing choices.
    if kind == 'Task' and (hour and not day or REMINDERS[reminder] >= 0 and (not day or hour is None)):
        due = 'Choose a date and time for this reminder'
    return {**item, 'title': title.strip(), 'kind': kind, 'category': category, 'due_date': due if kind == 'Task' else '', 'reminder': REMINDERS[reminder], 'duration': duration}


def calendar_actions(item, prefix):
    a, b = st.columns(2)
    a.download_button('Calendar + reminder', calendar_export([item]), 'campusrecall-event.ics', 'text/calendar', key=f'{prefix}_ics', icon=':material/calendar_month:', width='stretch')
    b.link_button('Add to Google Calendar', google_calendar_url(item), icon=':material/open_in_new:', width='stretch')



with st.sidebar:
    st.title('CampusRecall')
    st.caption('Remember it. Do it. Earn a star.')
    st.image(str(Path(__file__).with_name('assets') / 'ulm-life.jpg'), width='stretch', alt='ULM library beside the bayou at sunset')
    expo_mode = os.getenv('CAMPUSRECALL_EXPO_MODE', 'true').lower() != 'false'
    if expo_mode:
        mode = 'Expo visitor'
        st.badge('Expo', icon=':material/lock:', color='yellow')
    else:
        mode = st.radio('Workspace', ['Expo visitor', 'Personal'], key='workspace', on_change=reset_conversation)
    visitor = mode == 'Expo visitor'
    if not visitor:
        st.caption('Personal tasks are saved on this computer. This is a local, single-user workspace; it has no sign-in.')
    env_config = dotenv_values(Path(__file__).with_name('.env'))
    key = os.getenv('GEMINI_API_KEY', '') or env_config.get('GEMINI_API_KEY', '')
    if not key:
        try:
            key = st.secrets.get('GEMINI_API_KEY', '')
        except FileNotFoundError:
            key = ''

    model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-lite')
    if st.button('New conversation', key='new_conversation', icon=':material/chat:', width='stretch'):
        reset_conversation()
        st.rerun()
    if visitor and st.button('Next visitor · clear session', key='next_visitor', icon=':material/restart_alt:', width='stretch'):
        reset_conversation()
        st.session_state.visitor_items = []
        st.session_state.visitor_id = str(uuid4())
        st.session_state.notice = 'Ready for the next visitor.'
        st.session_state.page = 'Capture'
        st.session_state.pop('search', None)
        st.rerun()
    st.caption('Your submissions are analyzed by Gemini.')

@st.fragment(run_every=8)
def campus_banner():
    from PIL import Image, ImageOps
    photos = [('ulm-campus.jpg', 'ULM campus'), ('ulm-students.jpg', 'ULM computer science students'), ('ulm-life.jpg', 'Bayou sunset'), ('ulm-warhawks.jpg', 'Life at ULM'), ('ulm-viewbook.jpg', 'Discover ULM'), ('ulm-learning.jpg', 'Learning and careers at ULM'), ('ulm-graduation.png', 'ULM commencement')]
    index = int(time.monotonic() // 8) % len(photos)
    filename, caption = photos[index]
    with Image.open(Path(__file__).with_name('assets') / filename) as source:
        banner = ImageOps.pad(source.convert('RGB'), (1200, 400), color='#840029')
    st.image(banner, width='stretch', alt=caption)

hero, photo = st.columns([1, 1.25], gap='large', vertical_alignment='center')
with hero:
    st.badge('CAMPUSRECALL', color='yellow')
    st.title('Less to remember. More to do.')
    st.caption('Capture a thought. We’ll help with the next step.')
with photo:
    campus_banner()
if st.session_state.notice:
    st.success(st.session_state.notice)
    st.session_state.notice = ''
items = get_items()
today = datetime.now(ZONE).strftime('%Y-%m-%d')
open_tasks = [x for x in items if x['kind'] == 'Task' and not x['done']]
due_today = [x for x in open_tasks if x['due_date'].startswith(today)]
if 'next_page' in st.session_state:
    st.session_state.page = st.session_state.pop('next_page')
col1, col2, col3 = st.columns(3)
col1.metric('To do', len(open_tasks))
col2.metric('Today', len(due_today))
stars = sum(x['kind'] == 'Task' and bool(x['done']) for x in items)
col3.metric('Stars earned', f'⭐ {stars}', help='One star per completed task. Reopening or deleting a completed task removes its star.')
if st.session_state.pop('star_celebration', False):
    st.toast('Task complete! +1 star', icon='⭐')
page = st.segmented_control('Explore', ['Capture', 'Review', 'Today', 'My recall', 'Take away'], key='page', required=True, label_visibility='collapsed')

if page == 'Capture':
    st.subheader('What’s on your mind?')
    if not st.session_state.messages:
        sample_columns = st.columns(len(SAMPLES))
        for column, (label, sample) in zip(sample_columns, SAMPLES.items()):
            if column.button(label, key=f'sample_{label}', width='stretch'):
                st.session_state[f'capture_text_{st.session_state.revision}'] = sample
    for message in st.session_state.messages:
        with st.chat_message(message['role']):
            st.write(message['content'])
    if st.session_state.drafts and st.button('Review cards', key='review_cards', type='primary'):
        st.session_state.next_page = 'Review'
        st.rerun()
    revision = st.session_state.revision
    with st.form(f'capture_{revision}', clear_on_submit=False):
        text = st.text_area('Say it in your own words', key=f'capture_text_{revision}', placeholder='Let’s meet for lunch tomorrow…', height=110)
        with st.expander('Speak or attach a screenshot'):
            audio = st.audio_input('Record your thought', key=f'audio_{revision}')
            image = st.file_uploader('Screenshot or photo', type=['png', 'jpg', 'jpeg'], key=f'image_{revision}')
        submitted = st.form_submit_button('Help me remember', icon=':material/auto_awesome:', type='primary', width='stretch')
    if submitted:
        if not key:
            st.error('The assistant is not configured yet. Set GEMINI_API_KEY in the project’s .env file.')
        elif not text.strip() and not audio and not image:
            st.warning('Type a thought, record your voice, or attach a screenshot.')
        elif audio and image:
            st.warning('Send one attachment at a time: a recording or an image.')
        else:
            attachment = audio if audio else image
            if attachment and attachment.size > 15 * 1024 * 1024:
                st.error('Please use an attachment smaller than 15 MB.')
            else:
                message = text.strip() or ('[Voice recording]' if audio else '[Screenshot]')
                conversation = st.session_state.messages + [{'role': 'user', 'content': message}]
                try:
                    with st.spinner('Making sense of what matters…'):
                        reply, drafts = converse(conversation, st.session_state.drafts, items, key,
                            attachment.getvalue() if attachment else None, attachment.type if attachment else None, model)
                    st.session_state.messages = conversation + [{'role': 'assistant', 'content': reply}]
                    st.session_state.drafts = drafts
                    st.session_state.pop('retry_text', None)
                    st.session_state.revision += 1
                    if drafts:
                        st.session_state.next_page = 'Review'
                    st.rerun()
                except Exception as error:
                    st.error(assistant_error(error))
                    st.caption('Your input, saved items, and existing drafts are preserved. Retry after resolving the issue.')
                    st.session_state.retry_text = text
    if st.session_state.get('retry_text'):
        with st.expander('Your last submitted text'):
            st.text(st.session_state.retry_text)
elif page == 'Review':
    st.subheader('Make it yours')
    st.caption('Check your cards, then save.')
    if st.session_state.messages and st.session_state.messages[-1]['role'] == 'assistant':
        st.write(st.session_state.messages[-1]['content'])
    if not st.session_state.drafts:
        st.caption('Capture a thought to get started.')
    if st.button('Back to conversation', key='back_capture'):
        st.session_state.next_page = 'Capture'
        st.rerun()
    if st.session_state.drafts:
        with st.form(f'review_{st.session_state.revision}'):
            selected = []
            card_columns = st.columns(2, gap='large')
            for i, item in enumerate(st.session_state.drafts):
                prefix = f'draft_{st.session_state.revision}_{i}'
                with card_columns[i % 2].container(border=True):
                    include = st.checkbox('Keep this', value=True, key=f'{prefix}_include')
                    edited = item_fields(item, prefix)
                    if item['source']:
                        with st.expander('Original context'):
                            st.write(item['source'])
                    if include:
                        selected.append(edited)
            save = st.form_submit_button('Save reviewed items', type='primary', width='stretch')
        if save:
            try:
                for item in selected:
                    if not item['title']:
                        raise ValueError('Give each selected item a title.')
                    validate_date(item['due_date'])
                if not selected:
                    st.warning('Select at least one item to keep.')
                else:
                    count = save_selected(selected)
                    st.session_state.drafts = []
                    st.session_state.revision += 1
                    st.session_state.notice = f'{count} saved.'
                    st.session_state.next_page = 'My recall'
                    st.rerun()
            except ValueError:
                st.error('Give each selected item a title, and select a date before choosing a time or reminder.')

elif page in ['Today', 'My recall']:
    st.subheader('Today' if page == 'Today' else 'My recall')
    search = st.text_input('Find a task or memory', placeholder='Try “Sam”, “lunch”, or “assignment”', key='search')
    kind_filter = st.segmented_control('Show', ['All', 'Tasks', 'Memories'], default='All', key='kind_filter')
    show_done = st.checkbox('Include completed tasks', key='show_done')
    visible = []
    for item in items:
        if not show_done and item['done']:
            continue
        if kind_filter == 'Tasks' and item['kind'] != 'Task' or kind_filter == 'Memories' and item['kind'] != 'Memory':
            continue
        if page == 'Today' and (item['kind'] != 'Task' or item['due_date'] and item['due_date'][:10] > today):
            continue
        if search.casefold() not in f"{item['title']} {item['source']} {item['category']}".casefold():
            continue
        visible.append(item)
    if page == 'Today':
        st.caption('Today, overdue & unscheduled.')
    if not visible:
        st.info('Nothing here yet.')
    for item in visible:
        with st.container(border=True):
            a, b = st.columns([5, 1])
            with a:
                if item['kind'] == 'Task':
                    done = st.checkbox(item['title'], value=bool(item['done']), key=f"done_{mode}_{item['id']}")
                    if done != bool(item['done']):
                        if visitor:
                            item['done'] = int(done)
                        else:
                            update_item('personal', item['id'], done=done)
                        if done:
                            st.session_state.star_celebration = True
                        st.rerun()
                else:
                    st.write(item['title'])
                when = item['due_date'] or ('Saved for later' if item['kind'] == 'Memory' else 'Time not set')
                cutoff = today if len(item['due_date']) == 10 else datetime.now(ZONE).strftime('%Y-%m-%d %H:%M')
                overdue = item['kind'] == 'Task' and not item['done'] and item['due_date'] and item['due_date'] < cutoff
                st.caption(f"{item['kind']} · {item['category']} · {when}" + (' · Overdue' if overdue else ''))
                if item.get('reminder', -1) >= 0:
                    label = next(label for label, value in REMINDERS.items() if value == item['reminder'])
                    st.caption(f'Calendar reminder: {label} · Export to activate')
                if item['source']:
                    with st.expander('Original context'):
                        st.write(item['source'])
                with st.expander('Edit saved item', icon=':material/edit:'):
                    with st.form(f"edit_{mode}_{item['id']}_{st.session_state.revision}"):
                        edited = item_fields(item, f"edit_{mode}_{item['id']}_{st.session_state.revision}")
                        apply = st.form_submit_button('Save changes', type='primary')
                    if apply:
                        try:
                            edited = normalize_item(edited)
                            if visitor:
                                item.update(edited)
                                if item['kind'] == 'Memory':
                                    item['done'] = 0
                            else:
                                edit_item('personal', item['id'], edited)
                            st.session_state.revision += 1
                            st.session_state.notice = 'Saved your changes.'
                            st.rerun()
                        except ValueError as error:
                            st.error(str(error))
                if item['kind'] == 'Task' and item['due_date'] and not item['done']:
                    calendar_actions(item, f"saved_{mode}_{item['id']}")
            with b:
                if st.button('Delete', key=f"delete_{mode}_{item['id']}", icon=':material/delete:'):
                    if visitor:
                        st.session_state.visitor_items = [x for x in items if x['id'] != item['id']]
                    else:
                        update_item('personal', item['id'], delete=True)
                    st.rerun()

elif page == 'Take away':
    st.subheader('Take it with you')
    if not items:
        st.info('Save a reviewed item first, then come back for your takeaway.')
    else:
        with st.expander('Preview card'):
            st.text(action_card(items))
        a, b, c = st.columns(3)
        a.download_button('Printable recall card · PDF', pdf_card(items), 'campusrecall-card.pdf', 'application/pdf', icon=':material/picture_as_pdf:', width='stretch')
        scheduled = [x for x in items if x['kind'] == 'Task' and not x['done'] and x['due_date']]
        b.download_button('Calendar file', calendar_export(items), 'campusrecall.ics', 'text/calendar', disabled=not scheduled, icon=':material/calendar_month:', width='stretch')
        c.download_button('Spreadsheet', csv_export(items), 'campusrecall.csv', 'text/csv', icon=':material/table:', width='stretch')
        st.caption('Import the calendar file, then check alerts. Google Calendar links use your default alerts.')
        for item in scheduled:
            with st.container(border=True):
                st.write(item['title'])
                calendar_actions(item, f"take_{item['id']}")

