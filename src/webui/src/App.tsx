import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { LayoutDashboard, Bot, Archive, HardDrive, Shield } from 'lucide-react'

interface StatCardProps {
  title: string;
  value: string;
  colorClass: string;
}

function StatCard({ title, value, colorClass }: StatCardProps) {
  return (
    <div className={'border rounded-lg p-4 ' + colorClass}>
      <p className='text-sm text-slate-400'>{title}</p>
      <p className='text-2xl font-bold mt-1'>{value}</p>
    </div>
  );
}

function Dashboard() {
  return (
    <div className='p-6'>
      <h1 className='text-2xl font-bold mb-6 text-white'>Dashboard</h1>
      <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4'>
        <StatCard title='CPU Usage' value='12%' colorClass='border-blue-500 bg-blue-500/10' />
        <StatCard title='Memory' value='4.2 GB' colorClass='border-green-500 bg-green-500/10' />
        <StatCard title='Storage' value='2.1 TB' colorClass='border-purple-500 bg-purple-500/10' />
        <StatCard title='Agents Active' value='40' colorClass='border-orange-500 bg-orange-500/10' />
      </div>
    </div>
  );
}

function Agents() {
  return (
    <div className='p-6'>
      <h1 className='text-2xl font-bold mb-4 text-white'>AI Agents</h1>
      <p className='text-slate-400'>40 agent stubs: APEX, CIPHER, CORE, FORGE, ATLAS, QUANTUM, GENESIS, ARCHITECT and tier agents.</p>
    </div>
  );
}

function Compression() {
  return (
    <div className='p-6'>
      <h1 className='text-2xl font-bold mb-4 text-white'>Compression</h1>
      <p className='text-slate-400'>Compression pipeline status and job queue.</p>
    </div>
  );
}

function Storage() {
  return (
    <div className='p-6'>
      <h1 className='text-2xl font-bold mb-4 text-white'>Storage</h1>
      <p className='text-slate-400'>Disk usage, RAID status, volume management.</p>
    </div>
  );
}

const navItems = [
  { to: '/', label: 'Dashboard', Icon: LayoutDashboard },
  { to: '/agents', label: 'Agents', Icon: Bot },
  { to: '/compression', label: 'Compression', Icon: Archive },
  { to: '/storage', label: 'Storage', Icon: HardDrive },
];

export default function App() {
  return (
    <BrowserRouter>
      <div className='flex min-h-screen bg-slate-950 text-slate-100'>
        <nav className='w-56 bg-slate-900 border-r border-slate-800 flex flex-col shrink-0'>
          <div className='p-4 border-b border-slate-800'>
            <div className='flex items-center gap-2'>
              <Shield className='text-blue-400' size={20} />
              <span className='font-bold text-white'>SigmaVault</span>
            </div>
            <p className='text-xs text-slate-500 mt-1'>NAS OS v0.3.0</p>
          </div>
          <div className='flex-1 p-2'>
            {navItems.map(({ to, label, Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  isActive
                    ? 'flex items-center gap-3 px-3 py-2 rounded-md text-sm mb-1 bg-blue-600 text-white'
                    : 'flex items-center gap-3 px-3 py-2 rounded-md text-sm mb-1 text-slate-400 hover:text-white hover:bg-slate-800'
                }
              >
                <Icon size={16} />
                {label}
              </NavLink>
            ))}
          </div>
        </nav>
        <main className='flex-1 overflow-auto'>
          <Routes>
            <Route path='/' element={<Dashboard />} />
            <Route path='/agents' element={<Agents />} />
            <Route path='/compression' element={<Compression />} />
            <Route path='/storage' element={<Storage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
