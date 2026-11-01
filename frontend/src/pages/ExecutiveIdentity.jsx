import { useEffect, useState } from 'react';
import { Check, Crown, Pencil, Shield } from 'lucide-react';
import Button from '../components/Button.jsx';

export default function ExecutiveIdentity({ profile, onSave }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(profile);

  useEffect(() => setForm(profile), [profile]);
  function update(field, value) { setForm((current) => ({ ...current, [field]: value })); }
  function save() { onSave(form); setEditing(false); }

  const fields = [
    ['Full name', 'name'], ['Professional title', 'title'], ['Company', 'company'],
    ['Industry', 'industry'], ['Company valuation', 'valuation'], ['Personal net worth', 'netWorth'],
  ];

  return (
    <>
      <div className="page-intro">
        <div><div className="eyebrow">THE PERSON BEHIND THE PORTFOLIO</div><h1>Executive identity</h1><p>Your reputation precedes you. Make sure it says exactly what you intend.</p></div>
        <Button onClick={() => editing ? save() : setEditing(true)}>{editing ? <><Check size={15} /> Save profile</> : <><Pencil size={15} /> Edit profile</>}</Button>
      </div>
      <div className="identity-layout">
        <article className="identity-card">
          <div className="identity-card-top"><span>STERLING CAPITAL GROUP</span><Crown size={17} /></div>
          <div className="identity-monogram">{profile.name.split(' ').map((part) => part[0]).join('')}</div>
          <h2>{profile.name}</h2><p>{profile.title}</p>
          <div className="identity-card-rule" />
          <div className="identity-card-bottom"><b>F</b><span>FOUNDERS-ONLY<small>MEMBER SINCE 2019</small></span><i>NEW YORK</i></div>
        </article>
        <div className="identity-details">
          <section className="welcome-note"><span>✳ A NOTE FROM YOUR PRIVATE OFFICE</span><h2>Welcome back, {profile.name.split(' ')[0]}.</h2><p>Your presence changes the room. We have made sure your office is ready for what comes next.</p></section>
          <section className="panel profile-info">
            <div className="panel-heading"><div><div className="eyebrow">PERSONAL DOSSIER</div><h3>At a glance</h3></div><span className="secure-label"><Shield size={13} /> CONFIDENTIAL</span></div>
            <div className="info-grid">
              {fields.map(([label, key]) => <label className="info-field" key={key}><span>{label}</span>{editing ? <input value={form[key]} onChange={(event) => update(key, event.target.value)} /> : <b>{profile[key]}</b>}</label>)}
            </div>
            <label className="info-field bio-field"><span>Professional biography</span>{editing ? <textarea value={form.bio} onChange={(event) => update('bio', event.target.value)} /> : <p>{profile.bio}</p>}</label>
          </section>
          <section className="company-strip"><div className="company-icon"><Crown size={18} /></div><span><small>YOUR COMPANY</small><b>{profile.company}</b></span><span><small>VALUATION</small><b>{profile.valuation}</b></span></section>
        </div>
      </div>
    </>
  );
}
