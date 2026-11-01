import { useEffect, useState } from 'react';
import { Check, Crown, Pencil, Shield } from 'lucide-react';
import Button from '../components/Button.jsx';
import { apiRequest } from '../lib/api';

// 三大 LARP 核心戏精剧本预设
const PERSONA_PRESETS = [
  {
    id: 'arrogant_founder',
    name: 'The Unicorn Mogul (硅谷百亿独角兽创始人)',
    desc: '傲慢自负，张口闭口“底层逻辑”、“生态闭环”与“AGI 终局”。',
  },
  {
    id: 'toxic_hacker',
    name: 'The Toxic 10x Engineer (10x 毒舌系统架构师)',
    desc: '极度刻薄，喜欢嘲讽一切不懂汇编和把 div 居中的普通人。',
  },
  {
    id: 'bureaucrat',
    name: 'The Bureaucratic Black Hole (终极体制内行政主管)',
    desc: '无限踢皮球，习惯用极其正式繁琐的官方公文辞令回复一切。',
  },
];

export default function ExecutiveIdentity({ profile, onSave, onToast }) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(profile);

  useEffect(() => {
    setForm({
      ...profile,
      persona_preset: profile?.persona_preset || 'arrogant_founder',
    });
  }, [profile]);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function save() {
    setSaving(true);
    try {
      // 1. 同步给人设更新 API
      await apiRequest('/api/persona', {
        method: 'POST',
        body: JSON.stringify({
          name: form.name,
          title: form.title,
          company: form.company,
          industry: form.industry,
          valuation: form.valuation,
          netWorth: form.netWorth,
          bio: form.bio,
          persona_preset: form.persona_preset,
        }),
      });

      // 2. 更新本地状态并退出编辑
      if (onSave && !(await onSave(form))) return;
      setEditing(false);
      if (onToast) onToast('Executive profile synced to Agent successfully');
    } catch (err) {
      console.error('Failed to sync to backend:', err);
      if (onToast) onToast(err.message || 'Could not save profile. Please try again.');
    } finally {
      setSaving(false);
    }
  }

  // 保留所有暴发户核心字段
  const fields = [
    ['Full name', 'name'],
    ['Professional title', 'title'],
    ['Company', 'company'],
    ['Industry', 'industry'],
    ['Company valuation', 'valuation'],
    ['Personal net worth', 'netWorth'],
  ];

  const currentPreset =
    PERSONA_PRESETS.find((p) => p.id === form.persona_preset) || PERSONA_PRESETS[0];

  return (
    <>
      <div className="page-intro">
        <div>
          <div className="eyebrow">THE PERSON BEHIND THE PORTFOLIO</div>
          <h1>Executive identity</h1>
          <p>Your reputation precedes you. Make sure it says exactly what you intend.</p>
        </div>
        <Button onClick={() => (editing ? save() : setEditing(true))} disabled={saving}>
          {editing ? (
            <>
              <Check size={15} /> {saving ? 'Syncing...' : 'Save & Sync Agent'}
            </>
          ) : (
            <>
              <Pencil size={15} /> Edit profile
            </>
          )}
        </Button>
      </div>

      <div className="identity-layout">
        {/* 左侧实体卡片：保留豪门精英风格 */}
        <article className="identity-card">
          <div className="identity-card-top">
            <span>{form.company?.toUpperCase() || 'STERLING CAPITAL GROUP'}</span>
            <Crown size={17} />
          </div>
          <div className="identity-monogram">
            {form.name
              ? form.name
                  .split(' ')
                  .map((part) => part[0])
                  .join('')
              : 'AS'}
          </div>
          <h2>{form.name}</h2>
          <p>{form.title}</p>
          <div className="identity-card-rule" />
          <div className="identity-card-bottom">
            <b>F</b>
            <span>
              FOUNDERS-ONLY
              <small>NET WORTH: {form.netWorth || '$1.24B'}</small>
            </span>
            <i>ACTIVE</i>
          </div>
        </article>

        {/* 右侧详细档案 */}
        <div className="identity-details">
          <section className="welcome-note">
            <span>✳ AGENTIC DISPATCH POSTURE</span>
            <h2>Active Persona: {currentPreset.name.split(' (')[0]}</h2>
            <p>{currentPreset.desc}</p>
          </section>

          <section className="panel profile-info">
            <div className="panel-heading">
              <div>
                <div className="eyebrow">PERSONAL DOSSIER</div>
                <h3>At a glance</h3>
              </div>
              <span className="secure-label">
                <Shield size={13} /> CONFIDENTIAL
              </span>
            </div>

            {/* 剧本选择器 */}
            <div style={{ marginBottom: '1.25rem' }}>
              <label className="info-field">
                <span>LARP Executive Archetype</span>
                {editing ? (
                  <select
                    value={form.persona_preset}
                    onChange={(e) => update('persona_preset', e.target.value)}
                    style={{
                      background: 'var(--color-surface, #1e293b)',
                      color: '#fff',
                      border: '1px solid #475569',
                      padding: '8px',
                      borderRadius: '4px',
                      width: '100%',
                    }}
                  >
                    {PERSONA_PRESETS.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                ) : (
                  <b>{currentPreset.name}</b>
                )}
              </label>
            </div>

            {/* 6 个暴发户字段完全保留 */}
            <div className="info-grid">
              {fields.map(([label, key]) => (
                <label className="info-field" key={key}>
                  <span>{label}</span>
                  {editing ? (
                    <input
                      value={form[key] || ''}
                      onChange={(event) => update(key, event.target.value)}
                    />
                  ) : (
                    <b>{form[key]}</b>
                  )}
                </label>
              ))}
            </div>

            {/* 个人座右铭 / Bio */}
            <label className="info-field bio-field">
              <span>Professional biography</span>
              {editing ? (
                <textarea
                  value={form.bio || ''}
                  onChange={(event) => update('bio', event.target.value)}
                />
              ) : (
                <p>{form.bio}</p>
              )}
            </label>
          </section>

          {/* 底部醒目身价条 */}
          <section className="company-strip">
            <div className="company-icon">
              <Crown size={18} />
            </div>
            <span>
              <small>YOUR COMPANY</small>
              <b>{form.company}</b>
            </span>
            <span>
              <small>NET WORTH</small>
              <b style={{ color: '#eab308' }}>{form.netWorth}</b>
            </span>
            <span>
              <small>VALUATION</small>
              <b>{form.valuation}</b>
            </span>
          </section>
        </div>
      </div>
    </>
  );
}
