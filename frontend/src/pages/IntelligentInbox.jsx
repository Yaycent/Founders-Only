import { useEffect, useMemo, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { Mail, Search, Sparkles, Star } from 'lucide-react';
import { categories } from '../data/emails.js';

export default function IntelligentInbox({ emails: inboxEmails = [], selectedEmail, onSelectEmail }) {
  const [category, setCategory] = useState('All correspondence');
  const [query, setQuery] = useState('');
  const [emails, setEmails] = useState(inboxEmails);

  useEffect(() => setEmails(inboxEmails), [inboxEmails]);

  const active = selectedEmail || emails[0];

  const filtered = useMemo(() => emails.filter((email) => {
    const categoryMatch = category === 'All correspondence' || email.category === category;
    const searchMatch = `${email.name} ${email.subject} ${email.preview}`.toLowerCase().includes(query.toLowerCase());
    return categoryMatch && searchMatch;
  }), [emails, category, query]);

  function toggle(email, field) {
    if (!email) return;
    setEmails((current) => current.map((item) => item.id === email.id ? { ...item, [field]: !item[field] } : item));
    if (field === 'unread') onSelectEmail({ ...email, unread: !email.unread });
  }

  return (
    <>
      <div className="page-intro"><div><div className="eyebrow">YOUR CORRESPONDENCE, CONSIDERED</div><h1>Intelligent inbox</h1><p>Every conversation in its place. Every important matter, brought forward.</p></div></div>
      <div className="inbox-layout">
        <aside className="inbox-categories"><div className="eyebrow">MAILBOX</div>{categories.map((item, index) => <button className={category === item ? 'category active' : 'category'} key={item} onClick={() => setCategory(item)}><span>{String(index + 1).padStart(2, '0')}</span>{item}<small>{index === 0 ? emails.length : emails.filter((email) => email.category === item).length || '-'}</small></button>)}</aside>
        <section className="email-list">
          <div className="email-list-tools"><div><div className="eyebrow">{category.toUpperCase()}</div><small>{filtered.length} conversations</small></div><label className="search-box"><Search size={15} /><input placeholder="Search correspondence" value={query} onChange={(event) => setQuery(event.target.value)} /></label></div>
          {filtered.map((email) => <button className={`email-row ${active.id === email.id ? 'selected' : ''} ${email.unread ? 'unread' : ''}`} key={email.id} onClick={() => { onSelectEmail(email); if (email.unread) toggle(email, 'unread'); }}><span className="email-row-top"><b>{email.name}</b><time>{email.date}</time></span><strong>{email.subject}</strong><small>{email.preview}</small><span className="email-row-bottom"><i className={`priority-tag ${email.priority.toLowerCase()}`}>{email.priority}</i><span>{email.category}</span><i role="button" tabIndex={0} aria-label="Mark important" onClick={(event) => { event.stopPropagation(); toggle(email, 'important'); }}><Star size={15} fill={email.important ? 'currentColor' : 'none'} /></i></span></button>)}
          {!filtered.length && <p className="empty-state">No correspondence found.</p>}
        </section>
        <article className="email-detail">
          {active ? <>
            <div className="email-detail-actions"><button aria-label="Mark important" onClick={() => toggle(active, 'important')}><Star size={16} fill={active.important ? 'currentColor' : 'none'} /></button><button aria-label="Toggle read status" onClick={() => toggle(active, 'unread')}><Mail size={16} /></button></div>
            <div className="eyebrow">{active.category.toUpperCase()}</div><h2>{active.subject}</h2>
            <div className="sender-detail"><span className="sender-initial">{active.name.split(' ').map((part) => part[0]).join('')}</span><span><b>{active.name}</b><small>{active.email}</small></span><time>{active.date}</time></div>
            <div className="email-body">{active.body.split('\n').map((line, index) => <p key={index}>{line || ' '}</p>)}</div>
            <div className="email-reply-actions"><NavLink className="button button-gold" to="/studio"><Sparkles size={15} /> Reply with AI</NavLink><NavLink className="button button-outline" to="/studio">Reply</NavLink></div>
          </> : <p className="empty-state">No messages in this inbox.</p>}
        </article>
      </div>
    </>
  );
}
