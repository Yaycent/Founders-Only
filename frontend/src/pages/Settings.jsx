import { Link } from 'react-router-dom';
import { Bell, Check, Crown, FileText, Mail, Shield } from 'lucide-react';

const writingStyles = ['The Billionaire', 'The Ruthless CEO', 'The Diplomat', 'The Royal', 'The Busy Mogul', 'The Drama Queen', 'The Ice Cold', 'The Mastermind'];

export default function Settings({ profile, preferences, onSaveProfile, onChangePreferences }) {
  function update(field, value) { onChangePreferences({ ...preferences, [field]: value }); }

  return (
    <>
      <div className="page-intro"><div><div className="eyebrow">TUNED TO YOUR PREFERENCE</div><h1>Settings</h1><p>A private office should feel like yours. Consider it done.</p></div><span className="saved-indicator"><Check size={14} /> Changes save automatically</span></div>
      <div className="settings-layout">
        <nav className="settings-nav"><a href="#account">Account & identity</a><a href="#correspondence">Correspondence</a><a href="#briefing-preferences">Daily briefing</a><a href="#notifications">Notifications</a></nav>
        <div className="settings-content">
          <section className="settings-section" id="account"><div className="settings-title"><span><Crown size={17} /></span><div><h2>Account & identity</h2><p>Your presence in the room, and on the page.</p></div></div><div className="settings-row"><span><b>Executive profile</b><small>{profile.name} - {profile.title}</small></span><Link className="text-link" to="/identity">Manage profile</Link></div></section>
          <section className="settings-section" id="correspondence"><div className="settings-title"><span><Mail size={17} /></span><div><h2>Correspondence</h2><p>Your default voice and email preferences.</p></div></div><div className="settings-row"><span><b>Default writing style</b><small>Used when opening a new reply</small></span><select value={preferences.style} onChange={(event) => update('style', event.target.value)}>{writingStyles.map((style) => <option key={style}>{style}</option>)}</select></div><div className="settings-row"><span><b>Email signature</b><small>Include your executive sign-off</small></span><button className={`toggle ${preferences.emailSignature ? 'on' : ''}`} onClick={() => update('emailSignature', !preferences.emailSignature)}><i /></button></div></section>
          <section className="settings-section" id="briefing-preferences"><div className="settings-title"><span><FileText size={17} /></span><div><h2>Daily briefing</h2><p>Your morning, arranged on your terms.</p></div></div><div className="settings-row"><span><b>Daily delivery</b><small>Receive a briefing every morning</small></span><button className={`toggle ${preferences.briefing ? 'on' : ''}`} onClick={() => update('briefing', !preferences.briefing)}><i /></button></div><div className="settings-row"><span><b>Delivery time</b><small>{preferences.timezone}</small></span><select value={preferences.delivery} onChange={(event) => update('delivery', event.target.value)}>{['06:00 AM', '06:30 AM', '07:00 AM', '07:30 AM', '08:00 AM'].map((time) => <option key={time}>{time}</option>)}</select></div></section>
          <section className="settings-section" id="notifications"><div className="settings-title"><span><Bell size={17} /></span><div><h2>Notifications</h2><p>Only the matters worth interrupting you for.</p></div></div><div className="settings-row"><span><b>Priority notifications</b><small>Urgent matters and high-priority correspondence</small></span><button className={`toggle ${preferences.notifications ? 'on' : ''}`} onClick={() => update('notifications', !preferences.notifications)}><i /></button></div><p className="privacy-note"><Shield size={15} /> Your account data is private and stored on this device’s local database.</p></section>
        </div>
      </div>
    </>
  );
}
