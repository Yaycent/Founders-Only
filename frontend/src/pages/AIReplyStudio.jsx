import { useState } from 'react';
import { Copy, Send, Sparkles } from 'lucide-react';
import Button from '../components/Button.jsx';
import { mockEmails } from '../data/emails.js';
import { apiRequest } from '../lib/api.js';

const styles = [
  ['Saved executive persona', 'profile'],
  ['The Unicorn Mogul', 'arrogant_founder'],
  ['The Toxic 10x Architect', 'toxic_hacker'],
  ['The Bureaucratic Black Hole', 'bureaucrat'],
  ['The Billionaire', 'unicorn_gatekeeper'],
  ['The Ruthless CEO', 'reverse_recruiter'],
  ['The Diplomat', 'professional'],
  ['The Royal', 'negotiate'],
  ['The Busy Mogul', 'accept'],
  ['The Drama Queen', 'infinite_bureaucrat'],
  ['The Ice Cold', 'negotiate'],
  ['The Mastermind', 'reverse_recruiter'],
];

const actions = [
  'MAKE IT MORE EXPENSIVE',
  'SAVE MY REPUTATION',
  'REJECT WITH ELEGANCE',
  'MAKE ME SOUND IMPORTANT',
  'BUY ME SOME TIME',
  'MAKE IT MORE DOMINANT',
];

export default function AIReplyStudio({ emails = [], selectedEmail, onSelectEmail, onSendReply, onToast, profile }) {
  const [style, setStyle] = useState('Saved executive persona');
  const [action, setAction] = useState('');
  const [reply, setReply] = useState('');
  const [generating, setGenerating] = useState(false);
  const [sending, setSending] = useState(false);
  const source = selectedEmail || emails[0] || mockEmails[0];

  async function generate() {
    setGenerating(true);
    try {
      const { reply: generatedReply } = await apiRequest('/api/generate-reply', {
        method: 'POST',
        body: JSON.stringify({
          subject: source.subject,
          email_body: source.body,
          identity: profile,
          mode: styles.find(([label]) => label === style)?.[1] || 'professional',
          additional_direction: action,
        }),
      });
      setReply(generatedReply);
    } catch (error) {
      onToast(error.message);
    } finally {
      setGenerating(false);
    }
  }

  async function copyReply() {
    if (!reply) return onToast('Generate a reply first');
    await navigator.clipboard?.writeText(reply);
    onToast('Reply copied to clipboard');
  }

  function selectNextEmail() {
    const availableEmails = emails.length ? emails : mockEmails;
    const index = availableEmails.findIndex((item) => item.id === source.id);
    onSelectEmail(availableEmails[(index + 1) % availableEmails.length]);
    setReply('');
  }

  async function sendReply() {
    if (!reply.trim()) return onToast('Write or generate a reply first.');
    if (!window.confirm('Send this reply to the sender?')) return;
    setSending(true);
    const sent = await onSendReply(source.id, reply);
    setSending(false);
    if (sent) setReply('');
  }

  return (
    <>
      <div className="page-intro">
        <div>
          <div className="eyebrow">WORDS THAT OPEN DOORS</div>
          <h1>The reply studio</h1>
          <p>Your voice, with a little more leverage.</p>
        </div>
        <span className="studio-status">PRIVATE DRAFT</span>
      </div>

      <div className="studio-toolbar">
        <label>
          WRITE AS
          <select value={style} onChange={(event) => setStyle(event.target.value)}>
            {styles.map(([label]) => <option key={label}>{label}</option>)}
          </select>
        </label>
        <span><Sparkles size={14} /> A considered voice for consequential conversations.</span>
      </div>

      <div className="studio-grid">
        <section className="studio-card">
          <div className="eyebrow">THE CORRESPONDENCE</div>
          <h2>Original email</h2>
          <h3>{source.subject}</h3>
          <div className="sender-detail">
            <span className="sender-initial">
              {source.name.split(' ').map((part) => part[0]).join('')}
            </span>
            <span><b>{source.name}</b><small>{source.email}</small></span>
            <button className="plain-button" onClick={selectNextEmail}>Next email</button>
          </div>
          <div className="email-body">
            {source.body.split('\n').map((line, index) => <p key={index}>{line || ' '}</p>)}
          </div>
          <span className="category-chip">{source.category}</span>
        </section>

        <section className="studio-card editor-card">
          <div className="eyebrow">YOUR RESPONSE</div>
          <h2>Make it count.</h2>
          <textarea
            className="reply-editor"
            placeholder="Your words, thoughtfully arranged..."
            value={reply}
            onChange={(event) => setReply(event.target.value)}
          />
          <div className="editor-meta">
            <span>{reply.length} characters - {style}</span>
            <button onClick={copyReply}><Copy size={14} /> Copy</button>
          </div>
          <div className="action-label">OR GIVE IT A LITTLE DIRECTION</div>
          <div className="special-actions">
            {actions.map((item) => (
              <button
                className={action === item ? 'selected' : ''}
                key={item}
                onClick={() => setAction(action === item ? '' : item)}
              >
                {item}
              </button>
            ))}
          </div>
          <div className="studio-submit">
            <Button onClick={generate} disabled={generating}>
              <Sparkles size={15} />
              {generating ? 'Generating...' : reply ? 'Regenerate reply' : 'Generate reply'}
            </Button>
            <button
              className="plain-button"
              onClick={sendReply}
              disabled={sending || !source.id}
            >
              <Send size={14} /> {sending ? 'Sending...' : 'Send email'}
            </button>
          </div>
        </section>
      </div>

      <p className="privacy-note">Your correspondence remains private and under your control.</p>
    </>
  );
}
