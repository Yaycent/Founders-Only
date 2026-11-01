import { useState } from 'react';
import { Crown, Sparkles, Send, Copy, Check, Shield, Flame, Activity } from 'lucide-react';
import MoneyRain from '../components/MoneyRain.jsx';
import Button from '../components/Button.jsx';
import { apiRequest } from '../lib/api';

const PERSONA_PRESETS = [
  { id: 'arrogant_founder', name: 'The Unicorn Mogul', tag: '$42B AGI ENTITY', desc: 'Lives by first principles, closed loops, and the endgame. Rejections are overruled; Monday is your first day.' },
  { id: 'toxic_hacker', name: 'The Toxic 10x Architect', tag: '0.001ms LATENCY', desc: 'Dismisses anyone who cannot write assembly by hand or center a div.' },
  { id: 'bureaucrat', name: 'The Bureaucratic Black Hole', tag: 'FORM-404B ENFORCER', desc: 'Turns every incoming message into a compliance case and returns it with an official notice.' },
];

export default function Dashboard({ profile = {}, onToast }) {
  const [copied, setCopied] = useState(false);
  const [targetEmail, setTargetEmail] = useState('');
  const [scheduleType, setScheduleType] = useState('hyper_elite');
  const [sendingSchedule, setSendingSchedule] = useState(false);
  const [currentPersona, setCurrentPersona] = useState('arrogant_founder');

  // Agentboxd 分配给你的核心邮箱
  const AGENTBOXD_EMAIL = 'foundersonly@homingbox.net';

  // 1. 切换人设并即时同步到后端 Python
  async function handleSwitchPersona(presetId) {
    setCurrentPersona(presetId);
    try {
      await apiRequest('/api/persona', {
        method: 'POST',
        body: JSON.stringify({
          persona_preset: presetId,
          title: profile.title || 'Managing Partner & Chief Architect',
          name: profile.name || 'Alexander Sterling',
          netWorth: profile.netWorth || '$1.24B'
        }),
      });
      if (onToast) onToast(`Dossier Synced: Switched to ${presetId.toUpperCase()}`);
    } catch {
      if (onToast) onToast(`Persona updated locally`);
    }
  }

  // 2. 一键向现场评委的真实邮箱轰炸浮夸日程
  async function handleSendSchedule(e) {
    e.preventDefault();
    if (!targetEmail) return onToast?.('Please enter a target recipient email');
    
    setSendingSchedule(true);
    try {
      await apiRequest('/api/send-larp-schedule', {
        method: 'POST',
        body: JSON.stringify({
          email: targetEmail,
          request_type: scheduleType,
          persona: currentPersona,
        }),
      });
      if (onToast) onToast(`Executive schedule dispatched via Agentboxd to ${targetEmail}`);
      setTargetEmail('');
    } catch (err) {
      if (onToast) onToast(`Failed to dispatch schedule (Check backend status)`);
    } finally {
      setSendingSchedule(false);
    }
  }

  function copyEmail() {
    navigator.clipboard?.writeText(AGENTBOXD_EMAIL);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    if (onToast) onToast('Agentboxd address copied to clipboard');
  }

  const activePreset = PERSONA_PRESETS.find(p => p.id === currentPersona) || PERSONA_PRESETS[0];

  return (
    <div className="dashboard-content" style={{ maxWidth: '1100px', margin: '0 auto', padding: '2rem 1rem' }}>
      {/* 钞票雨特效：暴发户标配 */}
      <MoneyRain netWorth={profile.netWorth || '$1.24B'} />

      {/* 顶部：极度傲慢的标题栏 */}
      <section className="dashboard-welcome" style={{ marginBottom: '2.5rem', textAlign: 'center' }}>
        <div className="eyebrow" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: 'var(--gold)' }}>
          <Crown size={14} /> SOVEREIGN EXECUTIVE SUITE / PRIVATE TERMINAL
        </div>
        <h1 style={{ fontSize: '3rem', margin: '0.5rem 0', fontWeight: '800', letterSpacing: '-0.03em' }}>
          Welcome, <em>{profile.name || 'Alexander'}.</em>
        </h1>
        <p style={{ color: '#94a3b8', fontSize: '1.1rem', maxWidth: '600px', margin: '0 auto' }}>
          Your time is denominated in millions per second. Let the autonomous agents handle the mortals.
        </p>
      </section>

      {/* 第一核心区：身价与人设档案（极简黑金卡片） */}
      <div className="dashboard-card-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        
        {/* 档案卡片 */}
        <div className="dashboard-profile-card" style={{ background: 'linear-gradient(145deg, #1e2230, #11141d)', border: '1px solid rgba(255, 215, 0, 0.25)', borderRadius: '12px', padding: '1.8rem', position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', top: '-10px', right: '-10px', opacity: 0.05, transform: 'rotate(20deg)' }}>
            <Crown size={160} color="var(--gold)" />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--gold)', letterSpacing: '0.1em', fontWeight: '700' }}>NET WORTH / PERSONAL FORTUNE</span>
            <span style={{ background: 'rgba(189, 155, 92, 0.14)', color: 'var(--gold-bright)', fontSize: '0.75rem', padding: '2px 8px', borderRadius: '4px' }}>● LIVE MARKET</span>
          </div>
          <div style={{ fontSize: '3.2rem', fontWeight: '900', color: '#fff', letterSpacing: '-0.02em', margin: '0.5rem 0' }}>
            {profile.netWorth || '$1.24B'}
          </div>
          <div style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
            {profile.title || 'Managing Partner & Chief Architect'} • <b>{profile.company || 'Sterling Syndicate'}</b>
          </div>

          <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '1rem' }}>
            <small style={{ color: '#64748b', display: 'block', marginBottom: '8px', textTransform: 'uppercase' }}>Select Executive Persona:</small>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {PERSONA_PRESETS.map((p) => (
                <button
                  key={p.id}
                  onClick={() => handleSwitchPersona(p.id)}
                  style={{
                    background: currentPersona === p.id ? 'var(--gold)' : '#1a1813',
                    color: currentPersona === p.id ? '#000' : '#cbd5e1',
                    border: 'none',
                    padding: '6px 12px',
                    borderRadius: '6px',
                    fontSize: '0.8rem',
                    fontWeight: '700',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                >
                  {p.name.split(' (')[0]}
                </button>
              ))}
            </div>
            <p style={{ color: '#cbd5e1', fontSize: '0.85rem', marginTop: '10px', fontStyle: 'italic' }}>
              "{activePreset.desc}"
            </p>
          </div>
        </div>

        {/* 武器一：被动防御（对外的 Agentboxd 邮箱） */}
        <div className="dashboard-agent-card" style={{ background: 'linear-gradient(145deg, #171b26, #0e111a)', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '12px', padding: '1.8rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--gold-bright)', marginBottom: '0.5rem' }}>
              <Shield size={18} />
              <b style={{ letterSpacing: '0.05em', fontSize: '0.85rem' }}>AUTONOMOUS INBOUND GATEKEEPER</b>
            </div>
            <h3 style={{ fontSize: '1.4rem', color: '#fff', margin: '0.4rem 0' }}>The Reverse Rejection Proxy</h3>
            <p style={{ color: '#94a3b8', fontSize: '0.88rem', lineHeight: '1.5' }}>
              Forward any job rejection or partnership invitation to this private inbox. Your AI agent will overrule the decision in your chosen persona and announce its arrival by Monday.
            </p>
          </div>

          <div style={{ background: '#11100d', border: '1px dashed #514129', borderRadius: '8px', padding: '1rem', marginTop: '1rem' }}>
            <small style={{ color: '#64748b', display: 'block', textTransform: 'uppercase' }}>Inbound Dispatch Address:</small>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '4px' }}>
              <code style={{ fontSize: '1.05rem', color: 'var(--gold-bright)', fontWeight: 'bold' }}>{AGENTBOXD_EMAIL}</code>
              <button
                onClick={copyEmail}
                style={{ background: '#1a1813', border: '1px solid #514129', color: '#e7dcc2', padding: '4px 10px', borderRadius: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem' }}
              >
                {copied ? <Check size={12} color="var(--gold-bright)" /> : <Copy size={12} />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
          </div>

          <div style={{ marginTop: '1rem', display: 'flex', alignItems: 'center', gap: '8px', color: '#64748b', fontSize: '0.75rem' }}>
            <Activity size={13} color="#22c55e" />
            <span>Agentboxd background daemon running & listening</span>
          </div>
        </div>
      </div>

      {/* 武器二：主动出击（向评委真实邮箱投递离谱日程） */}
      <section className="dashboard-schedule-card" style={{ background: 'radial-gradient(ellipse at top, rgba(189,155,92,.12), #121210)', border: '1px solid rgba(189, 155, 92, 0.3)', borderRadius: '12px', padding: '2rem', boxShadow: '0 20px 40px rgba(0,0,0,0.4)' }}>
        <div style={{ maxWidth: '700px', margin: '0 auto', textAlign: 'center' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: 'var(--gold-bright)', fontSize: '0.85rem', fontWeight: '700', marginBottom: '0.5rem' }}>
            <Flame size={15} color="var(--gold-bright)" />
            LIVE DEMO INTERACTION: THE SCHEDULE FLEX
          </div>
          <h2 style={{ fontSize: '1.8rem', color: '#fff', margin: '0.3rem 0' }}>Send the Confidential Executive Schedule</h2>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
            Enter a recipient email below. Agentboxd will deliver a spectacular 24-hour executive itinerary, complete with ice baths, hand-written assembly, perfectly centered divs, and an unavoidable debate with Sam Altman.
          </p>

          <form onSubmit={handleSendSchedule} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              <input
                type="email"
                required
                value={targetEmail}
                onChange={(e) => setTargetEmail(e.target.value)}
                placeholder="Enter a recipient email (e.g. judge@larphacks.com)"
                style={{
                  flex: '1 1 300px',
                  background: 'rgba(22, 20, 15, 0.9)',
                  border: '1px solid #57462a',
                  padding: '12px 16px',
                  borderRadius: '6px',
                  color: '#fff',
                  fontSize: '0.95rem',
                  outline: 'none'
                }}
              />
              <select
                value={scheduleType}
                onChange={(e) => setScheduleType(e.target.value)}
                style={{
                  background: '#171510',
                  border: '1px solid #57462a',
                  padding: '12px',
                  borderRadius: '6px',
                  color: '#fff',
                  fontSize: '0.9rem',
                  outline: 'none'
                }}
              >
                <option value="hyper_elite">Billionaire Tech Mogul (Ice Baths / Alignment)</option>
                <option value="toxic_hacker">Underground 10x Architect (All-Nighters / Assembly)</option>
                <option value="bureaucrat">Bureaucratic Power Broker (Approvals / Stamps)</option>
              </select>
            </div>

            <Button
              type="submit"
              disabled={sendingSchedule}
              style={{
                background: 'linear-gradient(135deg, #d7bd83, #a8864d)',
                color: '#fff',
                fontWeight: 'bold',
                padding: '14px',
                fontSize: '1rem',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px'
              }}
            >
              <Sparkles size={18} />
              {sendingSchedule ? 'Agent is preparing and sending your schedule...' : 'Send the Confidential Schedule'}
            </Button>
          </form>
        </div>
      </section>
    </div>
  );
}
