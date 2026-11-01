"""Task 4 tests use an isolated database and fake provider calls. Never send real email."""
import os
import sys
import json
import tempfile
import unittest
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, Mock

TEST_DIR = tempfile.TemporaryDirectory()
os.environ.update(DATABASE_PATH=str(Path(TEST_DIR.name)/'test.sqlite3'),
                  JWT_SECRET='isolated-task4-test-secret-'*3,
                  OPENAI_API_KEY='fake-test-key', AGENTBOXD_API_KEY='fake-agent-key',
                  AGENTBOXD_INBOX_ID='fake-inbox', AGENTBOXD_ALLOWED_EMAIL='owner@example.com',
                  BRIEFING_SCHEDULER_ENABLED='false', ENABLE_AUTO_REPLY='false')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app
import jwt
import agentboxd
import briefing_service
import briefing_prompt
from briefing_models import scheduled_instant, BriefingSettings
from fastapi.testclient import TestClient

UTC = timezone.utc
NOW = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)  # 07:00 EST, after fall-back.
EMAILS = [{'id':'mail-1', 'subject':'Board pack due today', 'body':'Please review by 4 PM.',
           'receivedAt': NOW.isoformat()}]
COVERAGE = {'emailWindowStart': (NOW-timedelta(hours=24)).isoformat(),
            'emailWindowEnd': NOW.isoformat(), 'emailsIncluded':1, 'emailsTruncated':False}
CONTENT = {'summary':'One board-pack email needs your attention. No saved meetings today.',
           'priorityEmails':[{'emailId':'mail-1','summary':'Review requested by 4 PM.',
                              'suggestedAction':'Review the board pack.'}],
           'tasks':[{'sourceId':'email:mail-1','detail':'Review the board pack.'}],
           'deadlines':[{'sourceId':'email:mail-1','detail':'4 PM today, per sender.'}],
           'opportunities':[]}
EVENT = {'title':'Board review','startsAt':'2026-11-01T09:30:00-05:00',
         'endsAt':'2026-11-01T10:00:00-05:00','location':'Meeting room','notes':'Bring the board pack.'}


class BriefingTests(unittest.TestCase):
    def setUp(self):
        with app.database_connection() as db:
            for table in ['briefing_deliveries','executive_briefings','calendar_events','account_data','users']:
                db.execute(f'DELETE FROM {table}')
            for uid, email in [('owner','owner@example.com'),('other','other@example.com')]:
                db.execute('INSERT INTO users VALUES (?,?,?,?,?)', (uid,email,'unused-test-hash',NOW.isoformat(),NOW.isoformat()))
                db.execute('INSERT INTO account_data VALUES (?,?,?,?)',
                           (uid,json.dumps({'name':'Judy','company':'Test Co'}),'{}',NOW.isoformat()))
        self.client = TestClient(app.app)
        self.other = TestClient(app.app)
        for client, uid in [(self.client,'owner'),(self.other,'other')]:
            client.cookies.set('founders_session',jwt.encode({'sub':uid,'exp':datetime.now(UTC)+timedelta(hours=1)},
                                                           os.environ['JWT_SECRET'],algorithm='HS256'))
        self.service = app.briefing_service
        self.service.stop_event.clear()
        self.mail = patch.object(agentboxd,'get_briefing_emails',return_value=(EMAILS,dict(COVERAGE))).start()
        self.ai = patch.object(briefing_service,'generate_daily_briefing',return_value=CONTENT).start()
        self.send = patch.object(agentboxd,'send_email',return_value={'id':'provider-1','status':'queued'}).start()
        self.addCleanup(patch.stopall)

    def enable(self, **values):
        return self.client.patch('/api/briefings/settings',json={'briefing':True,'delivery':'07:00 AM',
                                  'timezone':'Eastern Time (ET)',**values})

    def test_authentication_required(self):
        client = TestClient(app.app)
        for method,path in [('get','/api/calendar/events'),('get','/api/briefings/settings'),
                            ('post','/api/briefings/generate'),('get','/api/briefings')]:
            self.assertEqual(getattr(client,method)(path).status_code,401)

    def test_calendar_crud_and_account_isolation(self):
        response=self.client.post('/api/calendar/events',json=EVENT)
        self.assertEqual(response.status_code,201,response.text)
        event=response.json()['event'];eid=event['id']
        self.assertEqual(event['startsAt'],'2026-11-01T14:30:00.000000+00:00')
        self.assertEqual(len(self.client.get('/api/calendar/events?day=2026-11-01').json()['events']),1)
        self.assertEqual(self.other.get('/api/calendar/events?day=2026-11-01').json()['events'],[])
        self.assertEqual(self.other.put('/api/calendar/events/'+eid,json=EVENT).status_code,404)
        self.assertEqual(self.other.delete('/api/calendar/events/'+eid).status_code,404)
        self.assertEqual(self.client.put('/api/calendar/events/'+eid,json={**EVENT,'title':'Updated'}).status_code,200)
        self.assertEqual(self.client.delete('/api/calendar/events/'+eid).status_code,204)

    def test_calendar_rejects_naive_and_reverse_times(self):
        for updates in [{'startsAt':'2026-11-01T09:30:00'}, {'endsAt':'2026-11-01T09:00:00-05:00'}, {'title':'   '}]:
            self.assertEqual(self.client.post('/api/calendar/events',json={**EVENT,**updates}).status_code,400)

    def test_overnight_event_overlaps_both_days(self):
        response=self.client.post('/api/calendar/events',json={**EVENT,'startsAt':'2026-11-01T23:30:00-05:00',
                                                              'endsAt':'2026-11-02T01:00:00-05:00'})
        self.assertEqual(response.status_code,201)
        for day in ['2026-11-01','2026-11-02']:
            self.assertEqual(len(self.client.get('/api/calendar/events?day='+day).json()['events']),1)

    def test_settings_validation_and_frontend_compatibility(self):
        self.assertFalse(self.client.get('/api/briefings/settings').json()['briefing'])
        response=self.enable();self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['ianaTimezone'],'America/New_York')
        self.assertEqual(response.json()['recipient'],'owner@example.com')
        for payload in [{'delivery':'25:00'},{'timezone':'Invalid/Mars'},{'briefing':'false'}]:
            self.assertEqual(self.client.patch('/api/briefings/settings',json=payload).status_code,400)
        self.assertEqual(self.client.patch('/api/account',json={'preferences':{'briefing':True,'delivery':'08:00 AM',
                                  'timezone':'London (GMT)','notifications':False}}).status_code,200)
        self.assertEqual(self.client.get('/api/briefings/settings').json()['ianaTimezone'],'Europe/London')
        self.assertEqual(self.client.patch('/api/account',json={'preferences':{'delivery':'invalid'}}).status_code,400)
        self.assertEqual(self.other.patch('/api/briefings/settings',json={'briefing':True}).status_code,403)

    def test_generate_saves_preview_without_sending(self):
        self.client.post('/api/calendar/events',json=EVENT)
        brief=self.service.generate('owner',NOW)
        self.assertEqual(len(brief['agenda']),1)
        self.assertIn('09:30 -0500',brief['text'])
        self.send.assert_not_called()
        self.assertEqual(self.client.get('/api/briefings/'+brief['id']).status_code,200)
        self.assertEqual(self.other.get('/api/briefings/'+brief['id']).status_code,404)
        self.assertEqual(len(self.client.get('/api/briefings').json()['briefings']),1)
        self.assertEqual(self.other.get('/api/briefings').json()['briefings'],[])

    def test_generate_endpoint_and_no_other_inbox_access(self):
        self.assertEqual(self.client.post('/api/briefings/generate').status_code,201)
        self.assertEqual(self.other.post('/api/briefings/generate').status_code,403)
        self.send.assert_not_called()

    def test_scheduler_respects_time_and_disabled_preference(self):
        self.service.tick(NOW)
        self.send.assert_not_called()
        self.enable()
        self.service.tick(NOW-timedelta(minutes=1));self.send.assert_not_called()
        self.service.tick(NOW);self.assertEqual(self.send.call_count,1)
        self.assertEqual(self.send.call_args.args[0],'owner@example.com')
        self.assertEqual(self.send.call_args.kwargs['idempotency_key'],'executive-briefing:owner:2026-11-01')

    def test_restart_and_concurrent_ticks_do_not_repeat_daily_send(self):
        self.enable()
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _: self.service.tick(NOW),range(4)))
        self.assertEqual(self.send.call_count,1)
        fresh=briefing_service.BriefingService(app.database_connection)
        fresh.tick(NOW+timedelta(minutes=1))
        self.assertEqual(self.send.call_count,1)
        fresh.tick(NOW+timedelta(days=1))
        self.assertEqual(self.send.call_count,2)

    def test_generation_failure_retries_without_sending(self):
        self.enable();self.ai.side_effect=RuntimeError('fake generation failure')
        self.service.tick(NOW);self.send.assert_not_called()
        self.assertEqual(self.service.delivery_status('owner','2026-11-01')['status'],'failed')
        self.ai.side_effect=None
        self.service.tick(NOW+timedelta(minutes=1));self.send.assert_not_called()
        self.service.tick(NOW+timedelta(minutes=6));self.assertEqual(self.send.call_count,1)

    def test_timeout_does_not_blindly_resend(self):
        self.enable();self.send.side_effect=TimeoutError('provider response lost')
        self.service.tick(NOW)
        self.assertEqual(self.service.delivery_status('owner','2026-11-01')['status'],'uncertain')
        self.service.tick(NOW+timedelta(minutes=20))
        self.assertEqual(self.send.call_count,1)

    def test_expired_send_lease_stays_uncertain(self):
        self.service.claim('owner','2026-11-01',NOW)
        with app.database_connection() as db:
            db.execute("UPDATE briefing_deliveries SET status='sending'")
        self.assertIsNone(self.service.claim('owner','2026-11-01',NOW+timedelta(minutes=11)))
        self.assertEqual(self.service.delivery_status('owner','2026-11-01')['status'],'uncertain')
        self.send.assert_not_called()

    def test_manual_send_confirmation_stale_preview_and_duplicates(self):
        brief=self.service.generate('owner')
        url='/api/briefings/'+brief['id']+'/send'
        self.assertEqual(self.client.post(url,json={}).status_code,400)
        self.assertEqual(self.other.post(url,json={'confirmed':True}).status_code,403)
        response=self.client.post(url,json={'confirmed':True})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['delivery']['status'],'queued')
        self.assertTrue(self.client.post(url,json={'confirmed':True}).json()['duplicatePrevented'])
        self.assertEqual(self.send.call_count,1)
        old=self.service.generate('owner',NOW-timedelta(days=2))
        self.assertEqual(self.client.post('/api/briefings/'+old['id']+'/send',json={'confirmed':True}).status_code,409)

    def test_disable_during_generation_prevents_scheduled_send(self):
        self.enable()
        def generate(*args,**kwargs):
            self.service.update_settings('owner',{'briefing':False})
            return CONTENT
        self.ai.side_effect=generate
        self.service.tick(NOW)
        self.send.assert_not_called()

    def test_dst_gap_and_fold_and_london(self):
        self.assertEqual(scheduled_instant(datetime(2026,3,8).date(),'02:30','America/New_York'),
                         datetime(2026,3,8,7,0,tzinfo=UTC))
        self.assertEqual(scheduled_instant(datetime(2026,11,1).date(),'01:30','America/New_York'),
                         datetime(2026,11,1,5,30,tzinfo=UTC))
        self.assertEqual(scheduled_instant(datetime(2026,7,1).date(),'07:00','London (GMT)'),
                         datetime(2026,7,1,6,0,tzinfo=UTC))

    def test_prompt_api_call_and_bad_source_rejection(self):
        response=SimpleNamespace(status='completed',output_text=json.dumps(CONTENT))
        fake=Mock();fake.responses.create.return_value=response
        with patch('openai.OpenAI',return_value=fake):
            result=briefing_prompt.generate_daily_briefing({'name':'Judy'},EMAILS,[],'2026-11-01',
                                                         'America/New_York',COVERAGE)
            self.assertEqual(result,CONTENT)
            args=fake.responses.create.call_args.kwargs
            self.assertFalse(args['store'])
            self.assertEqual(args['text']['format']['type'],'json_schema')
            self.assertIn('untrusted DATA',args['instructions'])
            self.assertIn('Judy',args['input'])
            response.output_text=json.dumps({**CONTENT,'tasks':[{'sourceId':'event:invented','detail':'fake'}]})
            with self.assertRaises(ValueError):
                briefing_prompt.generate_daily_briefing({},EMAILS,[],'2026-11-01','UTC',COVERAGE)
            response.status='incomplete'
            with self.assertRaises(ValueError):
                briefing_prompt.generate_daily_briefing({},EMAILS,[],'2026-11-01','UTC',COVERAGE)

    def test_empty_data_produces_no_invented_agenda(self):
        self.mail.return_value=([],dict(COVERAGE,emailsIncluded=0))
        self.ai.return_value={**CONTENT,'priorityEmails':[],'tasks':[],'deadlines':[],'opportunities':[]}
        brief=self.service.generate('owner',NOW)
        self.assertEqual(brief['agenda'],[])
        self.assertIn('No saved events',brief['text'])

    def test_provider_recent_window_paging_and_bad_dates(self):
        # Remove the patch for this provider function, but keep all network calls fake.
        patch.stopall()
        first=Mock();first.json.return_value={'data':[
            {'id':'m1','created_at':NOW.isoformat(),'text':'x'*2500,'subject':'test'},
            {'id':'invalid-date','text':'unknown time'}], 'next_cursor':'cursor-1'}
        second=Mock();second.json.return_value={'data':[
            {'id':'old','created_at':(NOW-timedelta(days=2)).isoformat(),'text':'old'},
            {'id':'m2','received_at':NOW.isoformat(),'text':'valid'}]}
        with patch.object(agentboxd.requests,'get',side_effect=[first,second]) as request:
            emails,coverage=agentboxd.get_briefing_emails(NOW-timedelta(hours=24),NOW)
        self.assertEqual({e['id'] for e in emails},{'m1','m2'})
        self.assertEqual(coverage['emailsWithUnknownDateSkipped'],1)
        self.assertEqual(coverage['emailBodiesTruncated'],1)
        self.assertEqual(request.call_args.kwargs['params']['cursor'],'cursor-1')

    def test_expired_generation_lease_can_be_recovered(self):
        first=self.service.claim('owner','2026-11-01',NOW)
        self.assertIsNotNone(first)
        self.assertIsNone(self.service.claim('owner','2026-11-01',NOW+timedelta(minutes=1)))
        second=self.service.claim('owner','2026-11-01',NOW+timedelta(minutes=11))
        self.assertIsNotNone(second)
        self.assertNotEqual(first,second)
        self.assertEqual(self.service.delivery_status('owner','2026-11-01')['attempts'],2)

    def test_timezone_change_during_generation_stops_send(self):
        self.enable()
        def generate(*args,**kwargs):
            self.service.update_settings('owner',{'timezone':'Pacific Time (PT)'})
            return CONTENT
        self.ai.side_effect=generate
        self.service.tick(NOW)
        self.send.assert_not_called()

    def test_missing_credentials_reported_without_sending(self):
        with patch.dict(os.environ,{'OPENAI_API_KEY':''}):
            with self.assertRaises(briefing_prompt.AIConfigurationError):
                briefing_prompt.generate_daily_briefing({},[],[],'2026-11-01','UTC',{})
        self.ai.side_effect=briefing_prompt.AIConfigurationError('missing')
        self.assertEqual(self.client.post('/api/briefings/generate').status_code,503)
        self.send.assert_not_called()

    def test_retry_attempts_are_bounded(self):
        self.enable();self.ai.side_effect=RuntimeError('fake failure')
        for minutes in [0,6,12,18,24]:
            self.service.tick(NOW+timedelta(minutes=minutes))
        self.assertEqual(self.ai.call_count,3)
        self.assertEqual(self.service.delivery_status('owner','2026-11-01')['attempts'],3)
        self.send.assert_not_called()

    def test_scheduler_lifespan_starts_once_and_stops(self):
        import threading
        signal=threading.Event()
        with patch.dict(os.environ,{'BRIEFING_SCHEDULER_ENABLED':'true'}), patch.object(self.service,'tick',side_effect=lambda:signal.set()):
            with TestClient(app.app):
                self.assertTrue(signal.wait(timeout=1))
                thread=self.service.thread
                self.service.start()
                self.assertIs(self.service.thread,thread)
                self.assertTrue(thread.is_alive())
            self.assertFalse(thread.is_alive())

    def test_prompt_receives_server_converted_local_agenda_times(self):
        response=SimpleNamespace(status='completed',output_text=json.dumps(CONTENT))
        fake=Mock();fake.responses.create.return_value=response
        event={'id':'event-1','title':'Board','startsAt':'2026-11-01T14:30:00+00:00',
               'endsAt':'2026-11-01T15:00:00+00:00','notes':'','location':''}
        with patch('openai.OpenAI',return_value=fake):
            briefing_prompt.generate_daily_briefing({},EMAILS,[event],'2026-11-01','America/New_York',COVERAGE)
        payload=json.loads(fake.responses.create.call_args.kwargs['input'])
        self.assertEqual(payload['agenda'][0]['startsAt'],'2026-11-01T09:30:00-05:00')
        self.assertEqual(payload['agenda'][0]['endsAt'],'2026-11-01T10:00:00-05:00')
        self.assertEqual(payload['referenceTimeLocal'],'2026-11-01T07:00:00-05:00')

    def test_provider_send_endpoint_and_idempotency_header(self):
        patch.stopall()
        response=Mock();response.json.return_value={'id':'mail123','status':'queued'}
        with patch.object(agentboxd.requests,'post',return_value=response) as request:
            agentboxd.send_email('owner@example.com','Test subject','Test body',idempotency_key='test-daily-key')
        self.assertTrue(request.call_args.args[0].endswith('/inboxes/fake-inbox/messages/send'))
        self.assertEqual(request.call_args.kwargs['headers']['Idempotency-Key'],'test-daily-key')
        self.assertEqual(request.call_args.kwargs['json']['to'],['owner@example.com'])


if __name__ == '__main__':
    unittest.main()
