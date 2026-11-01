import { NavLink } from 'react-router-dom';
import { Activity, ArrowRight, ArrowUpRight, CalendarDays, Clock3, Mail, TrendingUp } from 'lucide-react';
import MoneyRain from '../components/MoneyRain.jsx';
import StatCard from '../components/StatCard.jsx';
import { mockEmails } from '../data/emails.js';
import { briefing } from '../data/briefing.js';

export default function Dashboard({ profile, onSelectEmail }) {
  const recent = mockEmails.slice(0, 4);
  return (
    <>
      <MoneyRain netWorth={profile.netWorth} />
      <section className="welcome-row">
        <div>
          <div className="eyebrow"><i className="live-dot" /> SATURDAY, NOVEMBER 01, 2026 <span className="muted-inline">/ NEW YORK, 62°</span></div>
          <h1>Good morning, <em>{profile.name.split(' ')[0]}.</em></h1>
          <p className="welcome-subtitle">Your empire awaits. Let us get to business.</p>
        </div>
        <button className="date-button"><CalendarDays size={15} /> Saturday, November 01</button>
      </section>

      <section className="hero-panel">
        <div className="hero-copy">
          <span className="hero-kicker">YOUR PRIVATE OFFICE</span>
          <h2>Great fortunes are built<br />between the <em>lines.</em></h2>
          <p>Your day, distilled. The right decisions are waiting.</p>
          <NavLink className="text-link" to="/briefing">View your daily briefing <ArrowRight size={15} /></NavLink>
        </div>
        <div className="hero-emblem"><span>F</span></div>
        <div className="hero-index">VOL. 01 <i>/</i> YOUR DAILY EDITION</div>
      </section>

      <section className="stat-grid" aria-label="Executive overview">
        <StatCard label="TOTAL EMAILS" value="248" note="Across all correspondence" icon={Mail} trend="12% this week" />
        <StatCard label="PENDING REPLIES" value="11" note="4 require your attention" icon={Clock3} trend="Needs attention" warning />
        <StatCard label="HIGH PRIORITY" value="06" note="Matters of consequence" icon={Activity} trend="2 new today" />
        <StatCard label="OPPORTUNITIES" value="03" note="Awaiting your consideration" icon={TrendingUp} trend="+$42M potential" />
      </section>

      <div className="section-heading">
        <div><div className="eyebrow">THE DAILY DISPATCH</div><h2>At a glance</h2></div>
        <NavLink className="subtle-link" to="/briefing">Full briefing <ArrowRight size={14} /></NavLink>
      </div>

      <section className="dashboard-grid">
        <article className="panel correspondence-panel">
          <div className="panel-heading"><div><h3>Recent correspondence</h3><span>Your inbox, intelligently arranged</span></div><NavLink to="/inbox" className="round-arrow" aria-label="Open inbox"><ArrowRight size={15} /></NavLink></div>
          {recent.map((email) => (
            <button className="correspondence-row" key={email.id} onClick={() => onSelectEmail(email)}>
              <span className="sender-initial">{email.name.split(' ').map((part) => part[0]).join('')}</span>
              <span className="correspondence-copy"><b>{email.name}</b><small>{email.subject}</small></span>
              <i className={`priority-dot ${email.priority.toLowerCase()}`} />
              <time>{email.date}</time>
            </button>
          ))}
        </article>

        <article className="panel agenda-panel">
          <div className="panel-heading"><div><h3>Today’s agenda</h3><span>A day with intention</span></div><CalendarDays size={18} className="gold-icon" /></div>
          {briefing.agenda.slice(0, 3).map(([time, title, location]) => (
            <div className="agenda-row" key={time}><time>{time}</time><i /><span><b>{title}</b><small>{location}</small></span></div>
          ))}
          <NavLink className="agenda-more" to="/briefing">See full schedule <ArrowRight size={14} /></NavLink>
        </article>

        <article className="panel priority-panel">
          <div className="panel-heading"><div><h3>Matters of consequence</h3><span>Requiring your attention</span></div><b className="count-pill">03</b></div>
          {briefing.tasks.map((task, index) => <div className="task-row" key={task}><span>0{index + 1}</span><b>{task}</b><ArrowUpRight size={14} /></div>)}
        </article>

        <article className="business-panel">
          <div className="eyebrow">{profile.company.toUpperCase()}</div>
          <h3>Built for <em>the long view.</em></h3>
          <div className="business-stats"><span><small>PORTFOLIO VALUE</small><b>$1.24B</b></span><span><small>ACTIVE INVESTMENTS</small><b>18</b></span></div>
          <div className="business-health"><i /> PORTFOLIO HEALTH: EXCELLENT</div>
        </article>
      </section>
    </>
  );
}
