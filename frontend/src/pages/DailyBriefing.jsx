import { useState } from 'react';
import { ArrowRight, CalendarDays, Clock3, FileText, Sparkles, TrendingUp } from 'lucide-react';
import Button from '../components/Button.jsx';
import { briefing } from '../data/briefing.js';

export default function DailyBriefing({ preferences, onChange, onToast }) {
  const [refreshed, setRefreshed] = useState(false);
  function update(field, value) { onChange({ ...preferences, [field]: value }); }

  return (
    <>
      <div className="page-intro"><div><div className="eyebrow">THE MORNING, MASTERED</div><h1>Daily briefing</h1><p>A clear view of the day, before the day has a chance to begin.</p></div><Button onClick={() => { setRefreshed(true); onToast('Your briefing has been refreshed'); }}><Sparkles size={15} /> Generate briefing</Button></div>
      <div className="briefing-layout">
        <div className="briefing-main">
          <section className="briefing-cover"><div className="cover-label"><span>STERLING CAPITAL GROUP</span><span>PRIVATE OFFICE / NO. 304</span></div><div className="cover-date">SATURDAY <b>01</b> NOVEMBER 2026</div><h2>Your empire<br />awaits.</h2><p>{refreshed ? 'Your briefing has been refreshed.' : 'A considered beginning to a consequential day.'}</p><div className="cover-label cover-bottom"><span>DAILY EXECUTIVE BRIEFING</span><span>NEW YORK / 07:00 AM</span></div></section>
          <section className="panel summary-panel"><div className="eyebrow">THE EXECUTIVE SUMMARY</div><p>Today calls for decisive stewardship. A potential strategic acquisition, a high-conviction investment allocation, and a time-sensitive term sheet each merit your attention. Your calendar leaves space for the decisions that matter.</p></section>
          <section className="brief-section"><div className="section-heading compact"><div><div className="eyebrow">01 - YOUR DAY</div><h2>Today’s agenda</h2></div><CalendarDays size={17} /></div>{briefing.agenda.map(([time, title, place]) => <div className="schedule-row" key={time}><time>{time}</time><span><b>{title}</b><small>{place}</small></span></div>)}</section>
          <div className="briefing-columns">
            <section className="brief-section"><div className="eyebrow">02 - NEEDS YOUR ATTENTION</div><h2>Priority tasks</h2>{briefing.tasks.map((task, index) => <div className="brief-list-row" key={task}><span>0{index + 1}</span>{task}<ArrowRight size={13} /></div>)}</section>
            <section className="brief-section"><div className="eyebrow">03 - ON THE HORIZON</div><h2>Important deadlines</h2>{briefing.deadlines.map((deadline) => <div className="brief-list-row" key={deadline}><Clock3 size={14} />{deadline}</div>)}</section>
          </div>
          <section className="brief-section"><div className="eyebrow">04 - CONSIDERED OPPORTUNITIES</div><h2>Where possibility lives.</h2><div className="opportunity-grid">{briefing.opportunities.map(([name, detail]) => <article className="opportunity-card" key={name}><TrendingUp size={17} /><b>{name}</b><small>{detail}</small></article>)}</div></section>
        </div>
        <aside className="briefing-aside">
          <section className="panel delivery-card"><div className="eyebrow">YOUR PREFERENCE</div><h2>The ritual, your way.</h2><label className="toggle-row"><span><b>Daily briefing</b><small>Delivered every morning</small></span><button className={`toggle ${preferences.briefing ? 'on' : ''}`} onClick={() => update('briefing', !preferences.briefing)}><i /></button></label><label className="select-setting">DELIVERY TIME<select value={preferences.delivery} onChange={(event) => update('delivery', event.target.value)}>{['06:00 AM', '06:30 AM', '07:00 AM', '07:30 AM', '08:00 AM'].map((time) => <option key={time}>{time}</option>)}</select></label><label className="select-setting">TIMEZONE<select value={preferences.timezone} onChange={(event) => update('timezone', event.target.value)}>{['Eastern Time (ET)', 'Central Time (CT)', 'Mountain Time (MT)', 'Pacific Time (PT)', 'London (GMT)'].map((zone) => <option key={zone}>{zone}</option>)}</select></label><div className="delivery-note"><Clock3 size={15} /> Arrives at {preferences.delivery} - {preferences.timezone}</div></section>
          <section className="panel preview-card"><div className="panel-heading"><div><div className="eyebrow">A GLIMPSE INSIDE</div><h3>Email preview</h3></div><FileText size={17} /></div><div className="email-preview"><small>FROM YOUR PRIVATE OFFICE</small><h4>Your Empire Awaits -<br />Daily Executive Briefing</h4><hr /><b>Good morning, Alexander.</b><p>The day is yours to shape. Here is what deserves your attention.</p><span>VIEW YOUR BRIEFING <ArrowRight size={11} /></span></div></section>
          <blockquote className="briefing-quote">“Time is the one luxury no fortune can replenish.”</blockquote>
        </aside>
      </div>
    </>
  );
}
