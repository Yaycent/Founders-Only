import { useMemo, useState } from 'react';
import { Copy, Send, Sparkles } from 'lucide-react';
import Button from '../components/Button.jsx';
import { mockEmails } from '../data/emails.js';

const styles = ['The Billionaire', 'The Ruthless CEO', 'The Diplomat', 'The Royal', 'The Busy Mogul', 'The Drama Queen', 'The Ice Cold', 'The Mastermind'];
const actions = ['MAKE IT MORE EXPENSIVE', 'SAVE MY REPUTATION', 'REJECT WITH ELEGANCE', 'MAKE ME SOUND IMPORTANT', 'BUY ME SOME TIME', 'MAKE IT MORE DOMINANT'];

export default function AIReplyStudio({ selectedEmail, onSelectEmail, onToast }) {
  const [style, setStyle] = useState('The Diplomat');
  const [action, setAction] = useState('');
  const [reply, setReply] = useState('');
  const source = selectedEmail || mockEmails[0];

  const generatedReply = useMemo(() => {
    const name = source.name.split(' ')[0];
    let message = 'Your perspective is appreciated. There is clear merit in continuing this conversation, and I would be pleased to find a time that works for both our teams.';
    if (action === 'BUY ME SOME TIME') message = 'My office is reviewing the details carefully. I would welcome the opportunity to return with a considered response by the end of the week.';
    if (action === 'REJECT WITH ELEGANCE') message = 'After thoughtful consideration, I must decline at this time. I have great respect for what you are building and hope we may find another occasion to work together.';
    if (action === 'MAKE IT MORE DOMINANT') message = 'We are prepared to move forward on terms that reflect the full strategic value of this opportunity. My team will share our position shortly.';
    if (style === 'The Ice Cold') message = 'We have reviewed the proposal. It does not meet our current criteria. Please keep us informed should the terms change.';
    if (style === 'The Billionaire') message = 'The best opportunities are built on exceptional alignment. I see the beginnings of one here, and would be glad to explore where it leads.';
    return `Dear ${name},\n\nThank you for bringing this to my attention. ${message}\n\nWarm regards,\nAlexander`;
  }, [action, source.name, style]);

  function generate() { setReply(generatedReply); }

  async function copyReply() {
    if (!reply) return onToast('Generate a reply first');
    await navigator.clipboard?.writeText(reply);
    onToast('Reply copied to clipboard');
  }

  return (
    <>
      <div className="page-intro"><div><div className="eyebrow">WORDS THAT OPEN DOORS</div><h1>The reply studio</h1><p>Your voice, with a little more leverage.</p></div><span className="studio-status">● PRIVATE DRAFT</span></div>
      <div className="studio-toolbar"><label>WRITE AS<select value={style} onChange={(event) => setStyle(event.target.value)}>{styles.map((item) => <option key={item}>{item}</option>)}</select></label><span><Sparkles size={14} /> A considered voice for consequential conversations.</span></div>
      <div className="studio-grid">
        <section className="studio-card"><div className="eyebrow">THE CORRESPONDENCE</div><h2>Original email</h2><h3>{source.subject}</h3><div className="sender-detail"><span className="sender-initial">{source.name.split(' ').map((part) => part[0]).join('')}</span><span><b>{source.name}</b><small>{source.email}</small></span><button className="plain-button" onClick={() => { const index = mockEmails.findIndex((item) => item.id === source.id); onSelectEmail(mockEmails[(index + 1) % mockEmails.length]); }}>Next email</button></div><div className="email-body">{source.body.split('\n').map((line, index) => <p key={index}>{line || ' '}</p>)}</div><span className="category-chip">{source.category}</span></section>
        <section className="studio-card editor-card"><div className="eyebrow">YOUR RESPONSE</div><h2>Make it count.</h2><textarea className="reply-editor" placeholder="Your words, thoughtfully arranged..." value={reply} onChange={(event) => setReply(event.target.value)} /><div className="editor-meta"><span>{reply.length} characters - {style}</span><button onClick={copyReply}><Copy size={14} /> Copy</button></div><div className="action-label">OR GIVE IT A LITTLE DIRECTION</div><div className="special-actions">{actions.map((item) => <button className={action === item ? 'selected' : ''} key={item} onClick={() => setAction(action === item ? '' : item)}>{item}</button>)}</div><div className="studio-submit"><Button onClick={generate}><Sparkles size={15} /> {reply ? 'Regenerate reply' : 'Generate reply'}</Button><button className="plain-button" onClick={() => { onToast('Mock email sent successfully'); setReply(''); }}><Send size={14} /> Send email</button></div></section>
      </div>
      <p className="privacy-note">Your correspondence remains private and under your control.</p>
    </>
  );
}
