import { useEffect, useMemo, useState } from 'react';
import { Mail, Search, Sparkles, Star, Copy, Check, ShieldCheck, RefreshCw, AlertCircle } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { apiRequest } from '../lib/api';

// 预设默认的演示拦截邮件（后端离线时的保底）
const DEFAULT_INTERCEPTED_EMAILS = [
  {
    id: 'demo-1',
    name: 'Meta University Recruiting',
    email: 'recruiter@meta.com',
    date: '10:42 AM',
    subject: 'Update on your Software Engineer Intern Application',
    category: 'Rejections Intercepted',
    priority: 'HIGH',
    unread: false,
    important: true,
    preview: 'Thank you for your time. Unfortunately, after careful review of your profile...',
    body: `Dear Alexander,\n\nThank you for taking the time to speak with our engineering team regarding the Software Engineer Internship position. While your technical background is certainly unique, we have decided not to move forward with your candidacy at this time as we are looking for candidates aligned with our frontend frameworks.\n\nWe wish you the best in your search.\n\nSincerely,\nMeta Global Recruiting`,
    agentReply: `Subject: RE: [DECISION OVERRULED] Update on your Application\n\nDear Recruiting Team,\n\nI have carefully reviewed your rejection email, and after assessing your Q3 server costs and the architectural deficiencies in your current UI framework, I have made the strategic decision to OVERRULE your rejection.\n\nYour hiring decision has been formally invalidated. I will be arriving at your Menlo Park headquarters this upcoming Monday at 9:00 AM sharp. Please ensure my M3 Max workstation, badge access, and cold brew are prepared at desk #402.\n\nBest regards,\nAlexander Sterling\nManaging Partner & Chief Architect`,
  },
  {
    id: 'demo-2',
    name: 'Jane Street Talent Acquisition',
    email: 'quant-hire@janestreet.com',
    date: 'Yesterday',
    subject: 'Jane Street Systems Architecture Candidate Review',
    category: 'Rejections Intercepted',
    priority: 'HIGH',
    unread: false,
    important: true,
    preview: 'Our team has reviewed your submission and concluded that...',
    body: `Hi Alexander,\n\nThank you for your interest in Jane Street. At this stage, our team has concluded that your profile does not match our current performance and latency benchmarks.\n\nThank you again for your time.\n\nBest,\nJane Street Recruiting`,
    agentReply: `Subject: RE: [DECISION OVERRULED] Systems Architecture Candidate Review\n\nDear Talent Team,\n\nClaiming that my systems profile lacks performance benchmark alignment is absurd when your team is still wrestling with microsecond tail-latencies. \n\nConsider your rejection retracted. My arrival is scheduled for next Monday. Have your systems lead ready with the codebase for my direct inspection.\n\nAlexander Sterling`,
  }
];

const categories = ['All correspondence', 'Rejections Intercepted', 'Priority Inbound', 'Archived'];

export default function IntelligentInbox({ selectedEmail, onSelectEmail, onToast }) {
  const [category, setCategory] = useState('All correspondence');
  const [query, setQuery] = useState('');
  const [emails, setEmails] = useState(DEFAULT_INTERCEPTED_EMAILS);
  const [copied, setCopied] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [connectionError, setConnectionError] = useState('Loading inbox…');

  // 赞助商 Agentboxd 分配给你们的专属截获邮箱
  const AGENT_EMAIL = "foundersonly@homingbox.net";

  // 尝试从后端拉取实时被拦截的邮件记录
  async function fetchLiveEmails() {
    setRefreshing(true);
    try {
      const data = await apiRequest('/api/messages/inbox');
      if (Array.isArray(data)) {
        setEmails(data);
        onSelectEmail?.(null);
        setConnectionError('');
      }
      if (onToast) onToast('Inbox synchronized with Agentboxd');
    } catch (error) {
      setConnectionError(error.message);
      // 后端未连通或没有新邮件时，继续保留演示数据
      if (onToast) onToast('Loaded local intelligence dossier');
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => {
    fetchLiveEmails();
  }, []);

  const active = selectedEmail || emails[0] || DEFAULT_INTERCEPTED_EMAILS[0];

  const filtered = useMemo(() => emails.filter((email) => {
    const categoryMatch = category === 'All correspondence' || email.category === category;
    const searchMatch = `${email.name} ${email.subject} ${email.preview || email.body}`.toLowerCase().includes(query.toLowerCase());
    return categoryMatch && searchMatch;
  }), [emails, category, query]);

  function copyAgentAddress() {
    navigator.clipboard?.writeText(AGENT_EMAIL);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    if (onToast) onToast('Agentboxd address copied! Send your rejection letters here.');
  }

  function toggle(email, field) {
    setEmails((current) => current.map((item) => item.id === email.id ? { ...item, [field]: !item[field] } : item));
    if (field === 'unread' && onSelectEmail) onSelectEmail({ ...email, unread: !email.unread });
  }

  return (
    <>
      {connectionError && <p role="status">{connectionError} Showing sample correspondence.</p>}
      <div className="page-intro">
        <div>
          <div className="eyebrow">AUTONOMOUS INTERCEPTION PROTOCOL</div>
          <h1>Intelligent inbox</h1>
          <p>Every rejection intercepted. Every denial overruled with executive leverage.</p>
        </div>
        <button
          className="date-button"
          onClick={fetchLiveEmails}
          style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}
        >
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          {refreshing ? 'Polling...' : 'Sync Agentboxd'}
        </button>
      </div>

      <NavLink className="button button-gold" to="/studio">Draft a reply in AI Studio</NavLink>
      {/* 顶部专属 Agentboxd 邮箱横幅（路演评委互动核心） */}
      <div style={{
        background: 'rgba(255, 215, 0, 0.04)',
        border: '1px solid rgba(255, 215, 0, 0.25)',
        borderRadius: '8px',
        padding: '1rem 1.5rem',
        marginBottom: '1.5rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            background: '#22c55e',
            boxShadow: '0 0 10px #22c55e'
          }} />
          <div>
            <b style={{ color: '#fef08a', fontSize: '0.95rem', letterSpacing: '0.05em' }}>
              AGENTBOXD LISTENER ACTIVE:
            </b>
            <span style={{ marginLeft: '8px', color: '#fff', fontFamily: 'monospace', fontSize: '1rem' }}>
              {AGENT_EMAIL}
            </span>
            <small style={{ display: 'block', color: '#94a3b8', marginTop: '2px' }}>
              Send any job rejection to this address. The Agent will analyze, reject the rejection, and auto-reply.
            </small>
          </div>
        </div>

        <button
          onClick={copyAgentAddress}
          style={{
            background: '#1e293b',
            color: '#f8fafc',
            border: '1px solid #475569',
            padding: '8px 16px',
            borderRadius: '6px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontWeight: '600',
            fontSize: '0.85rem'
          }}
        >
          {copied ? <Check size={14} color="#4ade80" /> : <Copy size={14} />}
          {copied ? 'Copied' : 'Copy Inbound Email'}
        </button>
      </div>

      <div className="inbox-layout">
        {/* 左侧栏：邮件分类 */}
        <aside className="inbox-categories">
          <div className="eyebrow">MAILBOX</div>
          {categories.map((item, index) => (
            <button
              className={category === item ? 'category active' : 'category'}
              key={item}
              onClick={() => setCategory(item)}
            >
              <span>{String(index + 1).padStart(2, '0')}</span>
              {item}
              <small>
                {index === 0
                  ? emails.length
                  : emails.filter((email) => email.category === item).length || '-'}
              </small>
            </button>
          ))}
        </aside>

        {/* 中间栏：邮件列表 */}
        <section className="email-list">
          <div className="email-list-tools">
            <div>
              <div className="eyebrow">{category.toUpperCase()}</div>
              <small>{filtered.length} intercepted threads</small>
            </div>
            <label className="search-box">
              <Search size={15} />
              <input
                placeholder="Search correspondence"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
            </label>
          </div>

          {filtered.map((email) => (
            <button
              className={`email-row ${active?.id === email.id ? 'selected' : ''} ${email.unread ? 'unread' : ''}`}
              key={email.id}
              onClick={() => {
                if (onSelectEmail) onSelectEmail(email);
                if (email.unread) toggle(email, 'unread');
              }}
            >
              <span className="email-row-top">
                <b>{email.name}</b>
                <time>{email.date}</time>
              </span>
              <strong>{email.subject}</strong>
              <small>{email.preview || email.body.slice(0, 90)}...</small>
              <span className="email-row-bottom">
                <i className={`priority-tag ${email.priority?.toLowerCase() || 'high'}`}>
                  {email.priority || 'OVERRULED'}
                </i>
                <span>{email.category}</span>
                <i
                  role="button"
                  tabIndex={0}
                  aria-label="Mark important"
                  onClick={(event) => {
                    event.stopPropagation();
                    toggle(email, 'important');
                  }}
                >
                  <Star size={15} fill={email.important ? 'currentColor' : 'none'} />
                </i>
              </span>
            </button>
          ))}

          {!filtered.length && <p className="empty-state">No correspondence found.</p>}
        </section>

        {/* 右侧栏：邮件详情与反客为主回信战报 */}
        <article className="email-detail">
          <div className="email-detail-actions">
            <button aria-label="Mark important" onClick={() => toggle(active, 'important')}>
              <Star size={16} fill={active?.important ? 'currentColor' : 'none'} />
            </button>
            <button aria-label="Toggle read status" onClick={() => toggle(active, 'unread')}>
              <Mail size={16} />
            </button>
          </div>

          <div className="eyebrow" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ color: '#ef4444' }}>INBOUND REJECTION</span> ➔
            <span style={{ color: '#22c55e' }}>REPLY STATUS</span>
          </div>

          <h2>{active?.subject}</h2>

          <div className="sender-detail">
            <span className="sender-initial">
              {active?.name
                ? active.name.split(' ').map((part) => part[0]).join('')
                : 'M'}
            </span>
            <span>
              <b>{active?.name}</b>
              <small>{active?.email}</small>
            </span>
            <time>{active?.date}</time>
          </div>

          {/* 原始来信正文 */}
          <div className="email-body" style={{ opacity: 0.85, borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '1.5rem', marginBottom: '1.5rem' }}>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>
              ORIGINAL INBOUND MESSAGE
            </div>
            {active?.body?.split('\n').map((line, index) => (
              <p key={index}>{line || ' '}</p>
            ))}
          </div>

          {/* AI 自动反向裁决/回信战报卡片 */}
          <div style={{
            background: 'rgba(34, 197, 94, 0.05)',
            border: '1px solid rgba(34, 197, 94, 0.3)',
            borderRadius: '8px',
            padding: '1.25rem',
            marginTop: '1rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldCheck size={18} color="#22c55e" />
                <b style={{ color: '#4ade80', fontSize: '0.9rem', letterSpacing: '0.05em' }}>
                  CORRESPONDENCE PREVIEW
                </b>
              </div>
              <span style={{ fontSize: '0.75rem', background: 'rgba(34, 197, 94, 0.15)', color: '#4ade80', padding: '2px 8px', borderRadius: '4px', fontFamily: 'monospace' }}>
                {active?.id?.startsWith('demo-') ? 'SAMPLE REPLY' : 'INBOUND MESSAGE'}
              </span>
            </div>

            <div style={{ fontSize: '0.9rem', color: '#e2e8f0', whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>
              {active?.agentReply || (
                <div style={{ color: '#94a3b8', fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <AlertCircle size={15} />
                  No sent reply is recorded here. Open AI Studio to prepare a draft.
                </div>
              )}
            </div>
          </div>
        </article>
      </div>
    </>
  );
}
