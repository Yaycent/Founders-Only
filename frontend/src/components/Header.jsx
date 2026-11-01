import { Bell, Menu } from 'lucide-react';
import { useLocation } from 'react-router-dom';

const titles = {
  '/': 'Dashboard',
  '/identity': 'Executive Identity',
  '/inbox': 'Intelligent Inbox',
  '/studio': 'AI Reply Studio',
  '/briefing': 'Daily Briefing',
  '/settings': 'Settings',
};

export default function Header({ user, onMenu }) {
  const { pathname } = useLocation();
  return (
    <header className="topbar">
      <button className="mobile-menu" onClick={onMenu} aria-label="Open navigation"><Menu size={20} /></button>
      <div className="breadcrumb"><span>PRIVATE OFFICE</span><i>/</i><b>{titles[pathname] || 'Dashboard'}</b></div>
      <div className="topbar-right">
        <span className="top-date">{new Intl.DateTimeFormat('en-US', { weekday: 'long', month: 'long', day: '2-digit' }).format(new Date()).toUpperCase()}</span>
        <button className="notification-button" aria-label="Notifications"><Bell size={18} /><i /></button>
        <span className="top-avatar">{user.email?.[0]?.toUpperCase()}</span>
      </div>
    </header>
  );
}
