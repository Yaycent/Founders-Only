import { NavLink } from 'react-router-dom';
import {
  Activity, CircleHelp, Crown, FileText, Inbox, LayoutDashboard, LogOut,
  Settings as SettingsIcon, Shield, Sparkles, X,
} from 'lucide-react';

const groups = [
  { label: 'OVERVIEW', items: [['/', 'Dashboard', LayoutDashboard]] },
  {
    label: 'MANAGEMENT',
    items: [
      ['/identity', 'Executive Identity', Crown],
      ['/inbox', 'Intelligent Inbox', Inbox],
      ['/studio', 'AI Reply Studio', Sparkles],
      ['/briefing', 'Daily Briefing', FileText],
    ],
  },
  { label: 'PREFERENCES', items: [['/settings', 'Settings', SettingsIcon]] },
];

export default function Sidebar({ profile, onLogout, open, onClose }) {
  const initials = profile.name.split(' ').map((part) => part[0]).join('').slice(0, 2);

  return (
    <aside className={`sidebar ${open ? 'sidebar-open' : ''}`}>
      <div className="brand-lockup">
        <span className="brand-mark"><Crown size={17} /></span>
        <span>FOUNDERS-ONLY<small>PRIVATE OFFICE</small></span>
        <button className="mobile-close" onClick={onClose} aria-label="Close navigation"><X size={18} /></button>
      </div>
      <div className="member-card">
        <span className="member-avatar">{initials}</span>
        <span><b>{profile.name}</b><small>{profile.title}</small></span>
      </div>
      <nav aria-label="Main navigation">
        {groups.map((group) => (
          <section className="nav-group" key={group.label}>
            <h2>{group.label}</h2>
            {group.items.map(([path, label, Icon]) => (
              <NavLink end={path === '/'} to={path} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} key={path} onClick={onClose}>
                <Icon size={17} /><span>{label}</span>
                {label === 'Intelligent Inbox' && <i className="nav-badge">4</i>}
              </NavLink>
            ))}
          </section>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <div className="club-note"><Shield size={17} /><span><b>THE INNER CIRCLE</b><small>Your private office is secure.</small></span></div>
        <button className="logout-link" onClick={onLogout}><LogOut size={15} /> Log out</button>
        <div className="sidebar-copyright"><span>© 2026 FOUNDERS-ONLY</span><CircleHelp size={14} /></div>
      </div>
    </aside>
  );
}
