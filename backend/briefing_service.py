"""Persistent daily briefings, per-account agenda and restart-safe daily dispatch."""
from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo

try:
    from . import agentboxd
    from .briefing_models import BriefingSettings, delivery_time, timezone_name, scheduled_instant
    from .briefing_prompt import generate_daily_briefing
except ImportError:
    import agentboxd
    from briefing_models import BriefingSettings, delivery_time, timezone_name, scheduled_instant
    from briefing_prompt import generate_daily_briefing

UTC = timezone.utc
log = logging.getLogger('founders.briefing')


class BriefingError(RuntimeError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def stamp(value=None):
    return (value or datetime.now(UTC)).astimezone(UTC).isoformat(timespec='microseconds')


def day_bounds(day, zone):
    tz = ZoneInfo(zone)
    return (datetime.combine(day, datetime.min.time(), tz).astimezone(UTC),
            datetime.combine(day + timedelta(days=1), datetime.min.time(), tz).astimezone(UTC))


class BriefingService:
    def __init__(self, database_connection):
        self.db = database_connection
        self.stop_event = threading.Event()
        self.thread = None
        with self.db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS calendar_events (
                    id TEXT PRIMARY KEY,
                    userId TEXT NOT NULL REFERENCES users(_id) ON DELETE CASCADE,
                    title TEXT NOT NULL, startsAt TEXT NOT NULL, endsAt TEXT NOT NULL,
                    location TEXT NOT NULL, notes TEXT NOT NULL, createdAt TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS calendar_events_user_start
                    ON calendar_events(userId,startsAt);
                CREATE TABLE IF NOT EXISTS executive_briefings (
                    id TEXT PRIMARY KEY,
                    userId TEXT NOT NULL REFERENCES users(_id) ON DELETE CASCADE,
                    localDate TEXT NOT NULL, timezone TEXT NOT NULL,
                    subject TEXT NOT NULL, content TEXT NOT NULL, text TEXT NOT NULL,
                    sources TEXT NOT NULL, generatedAt TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS executive_briefings_user_created
                    ON executive_briefings(userId,generatedAt);
                CREATE TABLE IF NOT EXISTS briefing_deliveries (
                    userId TEXT NOT NULL REFERENCES users(_id) ON DELETE CASCADE,
                    localDate TEXT NOT NULL, briefingId TEXT,
                    status TEXT NOT NULL, token TEXT NOT NULL, leaseUntil TEXT NOT NULL,
                    attempts INTEGER NOT NULL, retryAt TEXT NOT NULL,
                    errorCode TEXT, providerId TEXT, updatedAt TEXT NOT NULL,
                    PRIMARY KEY(userId,localDate)
                );
            ''')

    def account(self, user_id):
        with self.db() as db:
            row = db.execute('SELECT u.email,a.profile,a.preferences FROM users u '
                             'JOIN account_data a ON a.userId=u._id WHERE u._id=?', (user_id,)).fetchone()
        if row is None:
            raise BriefingError('Account was not found.', 404)
        return {'email': row['email'], 'profile': json.loads(row['profile']),
                'preferences': json.loads(row['preferences'])}

    def owner(self, user_id):
        account = self.account(user_id)
        allowed = os.environ.get('AGENTBOXD_ALLOWED_EMAIL', '').strip().lower()
        if not allowed:
            raise BriefingError('Agentboxd inbox owner is not configured.', 503)
        if account['email'].lower() != allowed:
            raise BriefingError('This account cannot access the connected inbox.', 403)
        return account

    def settings(self, user_id, now=None):
        values = BriefingSettings.model_validate(self.account(user_id)['preferences'])
        zone = timezone_name(values.timezone)
        now = now or datetime.now(UTC)
        today = now.astimezone(ZoneInfo(zone)).date()
        next_run = scheduled_instant(today, values.delivery, zone)
        status = self.delivery_status(user_id, str(today))
        if next_run <= now or (status and status['status'] in ('queued', 'uncertain')):
            next_run = scheduled_instant(today + timedelta(days=1), values.delivery, zone)
        return {**values.model_dump(), 'ianaTimezone': zone,
                'nextRunAt': stamp(next_run) if values.briefing else None,
                'schedulerEnabled': os.environ.get('BRIEFING_SCHEDULER_ENABLED', 'true').lower() == 'true',
                'recipient': self.account(user_id)['email']}

    def update_settings(self, user_id, updates):
        if updates.get('briefing'):
            self.owner(user_id)
        account = self.account(user_id)
        preferences = {**account['preferences'], **updates}
        BriefingSettings.model_validate(preferences)
        with self.db() as db:
            db.execute('UPDATE account_data SET preferences=?,updatedAt=? WHERE userId=?',
                       (json.dumps(preferences), stamp(), user_id))
        return self.settings(user_id)

    def events(self, user_id, day=None, zone=None):
        account = self.account(user_id)
        zone = zone or timezone_name(BriefingSettings.model_validate(account['preferences']).timezone)
        day = day or datetime.now(ZoneInfo(zone)).date()
        start, end = day_bounds(day, zone)
        with self.db() as db:
            rows = db.execute('SELECT id,title,startsAt,endsAt,location,notes FROM calendar_events '
                              'WHERE userId=? AND startsAt<? AND endsAt>? ORDER BY startsAt,id',
                              (user_id, stamp(end), stamp(start))).fetchall()
        return [dict(row) for row in rows]

    def save_event(self, user_id, event, event_id=None):
        self.account(user_id)
        values = (event.title, stamp(event.startsAt), stamp(event.endsAt), event.location, event.notes)
        with self.db() as db:
            if event_id:
                result = db.execute('UPDATE calendar_events SET title=?,startsAt=?,endsAt=?,location=?,notes=? '
                                    'WHERE id=? AND userId=?', (*values, event_id, user_id))
                if result.rowcount != 1:
                    raise BriefingError('Event was not found.', 404)
            else:
                event_id = str(uuid.uuid4())
                db.execute('INSERT INTO calendar_events VALUES (?,?,?,?,?,?,?,?)',
                           (event_id, user_id, *values, stamp()))
        return {'id': event_id, 'title': event.title, 'startsAt': values[1], 'endsAt': values[2],
                'location': event.location, 'notes': event.notes}

    def delete_event(self, user_id, event_id):
        with self.db() as db:
            result = db.execute('DELETE FROM calendar_events WHERE id=? AND userId=?', (event_id, user_id))
            if result.rowcount != 1:
                raise BriefingError('Event was not found.', 404)

    def generate(self, user_id, now=None):
        account = self.owner(user_id)
        prefs = BriefingSettings.model_validate(account['preferences'])
        zone = timezone_name(prefs.timezone)
        now = now or datetime.now(UTC)
        local_day = now.astimezone(ZoneInfo(zone)).date()
        agenda = self.events(user_id, local_day, zone)
        # Limit prompt size and declare incomplete coverage rather than silently truncate.
        agenda_truncated = len(agenda) > 50
        agenda = agenda[:50]
        notes_truncated = sum(len(item['notes']) > 500 for item in agenda)
        agenda = [{**item, 'notes': item['notes'][:500]} for item in agenda]
        emails, coverage = agentboxd.get_briefing_emails(now - timedelta(hours=24), now)
        coverage['agendaTruncated'] = agenda_truncated
        coverage['agendaNotesTruncated'] = notes_truncated
        coverage['calendarSource'] = 'Saved backend events; no external calendar is connected.'
        content = generate_daily_briefing(account['profile'], emails, agenda, local_day.isoformat(),
                                          zone, coverage, prefs.briefingLanguage)
        subject = f'Daily Executive Briefing — {local_day.isoformat()}'
        text = self.render(content, agenda, zone, local_day.isoformat(), coverage)
        brief = {'id': str(uuid.uuid4()), 'localDate': local_day.isoformat(), 'timezone': zone,
                 'subject': subject, 'content': content, 'agenda': agenda,
                 'coverage': coverage, 'text': text, 'generatedAt': stamp(now)}
        with self.db() as db:
            db.execute('INSERT INTO executive_briefings VALUES (?,?,?,?,?,?,?,?,?)',
                       (brief['id'], user_id, brief['localDate'], zone, subject, json.dumps(content),
                        text, json.dumps({'agenda': agenda, 'coverage': coverage}), brief['generatedAt']))
        return brief

    @staticmethod
    def render(content, agenda, zone, day, coverage):
        lines = [f'DAILY EXECUTIVE BRIEFING | {day} | {zone}', '', content['summary'], '', 'PRIORITY EMAILS']
        lines += [f"- {x['summary']} Suggested action: {x['suggestedAction']} [email:{x['emailId']}]"
                  for x in content['priorityEmails']] or ['- None identified.']
        lines += ['', "TODAY'S AGENDA"]
        for event in agenda:
            start = datetime.fromisoformat(event['startsAt']).astimezone(ZoneInfo(zone))
            end = datetime.fromisoformat(event['endsAt']).astimezone(ZoneInfo(zone))
            lines.append(f"- {start:%Y-%m-%d %H:%M %z} – {end:%Y-%m-%d %H:%M %z}: "
                         f"{event['title']} | {event['location']} [event:{event['id']}]")
        if not agenda:
            lines.append('- No saved events for today. External calendars are not connected.')
        for heading, key in [('PRIORITY TASKS', 'tasks'), ('IMPORTANT DEADLINES', 'deadlines'),
                             ('OPPORTUNITIES', 'opportunities')]:
            lines += ['', heading]
            lines += [f"- {x['detail']} [{x['sourceId']}]" for x in content[key]] or ['- None identified.']
        lines += ['', 'SOURCE COVERAGE',
                  f"Inbox: {coverage.get('emailsIncluded', 0)} messages received in the last 24 hours.",
                  'Calendar: saved events only; external calendars are not connected.']
        if coverage.get('emailsTruncated') or coverage.get('agendaTruncated'):
            lines.append('Coverage is limited: additional messages or events were not included.')
        if coverage.get('emailsWithUnknownDateSkipped'):
            lines.append('Some messages without a valid received timestamp were excluded.')
        if coverage.get('emailBodiesTruncated') or coverage.get('agendaNotesTruncated'):
            lines.append('Long email bodies or event notes were shortened before summarizing.')
        lines += ['', 'Prepared from source records. Suggested actions have not been performed.']
        return '\n'.join(lines)

    def get_briefing(self, user_id, briefing_id):
        with self.db() as db:
            row = db.execute('SELECT * FROM executive_briefings WHERE id=? AND userId=?',
                             (briefing_id, user_id)).fetchone()
        if row is None:
            raise BriefingError('Briefing was not found.', 404)
        brief = dict(row)
        brief.pop('userId')
        brief['content'] = json.loads(brief['content'])
        brief.update(json.loads(brief.pop('sources')))
        return brief

    def history(self, user_id, limit=20):
        with self.db() as db:
            rows = db.execute('SELECT b.id,b.localDate,b.subject,b.generatedAt,d.status AS deliveryStatus '
                              'FROM executive_briefings b LEFT JOIN briefing_deliveries d ON d.briefingId=b.id '
                              'WHERE b.userId=? ORDER BY b.generatedAt DESC LIMIT ?', (user_id, limit)).fetchall()
        return [dict(row) for row in rows]

    def delivery_status(self, user_id, local_day):
        with self.db() as db:
            row = db.execute('SELECT localDate,briefingId,status,attempts,retryAt,errorCode,providerId,updatedAt '
                             'FROM briefing_deliveries WHERE userId=? AND localDate=?',
                             (user_id, local_day)).fetchone()
        return dict(row) if row else None

    def claim(self, user_id, day, now):
        token = str(uuid.uuid4())
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM briefing_deliveries WHERE userId=? AND localDate=?',
                             (user_id, day)).fetchone()
            if row:
                if row['status'] in ('queued', 'uncertain'):
                    return None
                if row['status'] == 'sending':
                    if row['leaseUntil'] <= stamp(now):
                        db.execute("UPDATE briefing_deliveries SET status='uncertain',errorCode='send_interrupted',"
                                   'updatedAt=? WHERE userId=? AND localDate=?', (stamp(now), user_id, day))
                    return None
                if row['status'] == 'preparing' and row['leaseUntil'] > stamp(now):
                    return None
                if row['attempts'] >= 3 or row['retryAt'] > stamp(now):
                    return None
                db.execute("UPDATE briefing_deliveries SET status='preparing',token=?,leaseUntil=?,attempts=attempts+1,"
                           'errorCode=NULL,updatedAt=? WHERE userId=? AND localDate=?',
                           (token, stamp(now + timedelta(minutes=10)), stamp(now), user_id, day))
            else:
                db.execute('INSERT INTO briefing_deliveries '
                           '(userId,localDate,status,token,leaseUntil,attempts,retryAt,updatedAt) '
                           "VALUES (?,?,'preparing',?,?,1,?,?)",
                           (user_id, day, token, stamp(now + timedelta(minutes=10)), stamp(now), stamp(now)))
        return token

    def dispatch(self, user_id, briefing_id=None, now=None, scheduled=False):
        frozen_clock = now is not None
        now = now or datetime.now(UTC)
        account = self.owner(user_id)
        settings = BriefingSettings.model_validate(account['preferences'])
        day = now.astimezone(ZoneInfo(timezone_name(settings.timezone))).date().isoformat()
        brief = self.get_briefing(user_id, briefing_id) if briefing_id else None
        if brief and (brief['localDate'] != day or brief['timezone'] != timezone_name(settings.timezone)):
            raise BriefingError('Generate a new briefing for today and your current timezone.', 409)
        token = self.claim(user_id, day, now)
        if not token:
            return {'delivery': self.delivery_status(user_id, day), 'duplicatePrevented': True}
        sending = False
        try:
            if brief is None:
                brief = self.generate(user_id, now)
            # Re-read settings after generation; disabling while AI runs stops scheduled sending.
            if scheduled:
                latest = BriefingSettings.model_validate(self.account(user_id)['preferences'])
                current = now if frozen_clock else datetime.now(UTC)
                current_day = current.astimezone(ZoneInfo(timezone_name(latest.timezone))).date()
                if (self.stop_event.is_set() or not latest.briefing or str(current_day) != day or
                    timezone_name(latest.timezone) != timezone_name(settings.timezone) or
                    current < scheduled_instant(current_day, latest.delivery, timezone_name(latest.timezone))):
                    raise BriefingError('Delivery settings changed before sending.', 409)
            agentboxd.get_config()
            with self.db() as db:
                changed = db.execute("UPDATE briefing_deliveries SET status='sending',briefingId=?,updatedAt=? "
                                     "WHERE userId=? AND localDate=? AND token=? AND status='preparing'",
                                     (brief['id'], stamp(), user_id, day, token)).rowcount
            if changed != 1:
                raise BriefingError('Another worker owns this delivery.', 409)
            sending = True
            result = agentboxd.send_email(account['email'], brief['subject'], brief['text'],
                                           idempotency_key=f'executive-briefing:{user_id}:{day}')
            provider_id = str(result.get('id') or (result.get('data') or {}).get('id') or '')
            with self.db() as db:
                db.execute("UPDATE briefing_deliveries SET status='queued',providerId=?,updatedAt=? "
                           'WHERE userId=? AND localDate=? AND token=?',
                           (provider_id, stamp(), user_id, day, token))
        except Exception as error:
            # A lost response may follow a successful provider send. Never retry blindly.
            with self.db() as db:
                db.execute('UPDATE briefing_deliveries SET status=?,errorCode=?,retryAt=?,updatedAt=? '
                           'WHERE userId=? AND localDate=? AND token=?',
                           ('uncertain' if sending else 'failed', type(error).__name__,
                            stamp(now + timedelta(minutes=5)), stamp(), user_id, day, token))
            if isinstance(error, BriefingError):
                raise
            raise BriefingError('Briefing could not be queued. Check delivery status before retrying.', 502) from error
        return {'delivery': self.delivery_status(user_id, day), 'duplicatePrevented': False}

    def tick(self, now=None):
        frozen_clock = now is not None
        now = now or datetime.now(UTC)
        with self.db() as db:
            rows = db.execute('SELECT a.userId,a.preferences FROM account_data a JOIN users u ON u._id=a.userId '
                              'WHERE lower(u.email)=?', (os.environ.get('AGENTBOXD_ALLOWED_EMAIL', '').strip().lower(),)).fetchall()
        for row in rows:
            if self.stop_event.is_set():
                break
            try:
                prefs = BriefingSettings.model_validate(json.loads(row['preferences']))
                if not prefs.briefing:
                    continue
                zone = timezone_name(prefs.timezone)
                day = now.astimezone(ZoneInfo(zone)).date()
                if now >= scheduled_instant(day, prefs.delivery, zone):
                    self.dispatch(row['userId'], now=now if frozen_clock else None, scheduled=True)
            except Exception as error:
                # No secrets, private message text or raw provider errors in logs.
                log.warning('Daily briefing tick failed (%s).', type(error).__name__)

    def start(self):
        if os.environ.get('BRIEFING_SCHEDULER_ENABLED', 'true').lower() != 'true':
            return
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        def run():
            while not self.stop_event.is_set():
                try:
                    self.tick()
                except Exception as error:
                    log.warning('Briefing scheduler failed (%s).', type(error).__name__)
                self.stop_event.wait(30)
        self.thread = threading.Thread(target=run, name='daily-executive-briefing', daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1)
