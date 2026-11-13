import { LayoutDashboard, MessageSquare, TrendingUp } from 'lucide-react'

export default function Sidebar({ page, setPage }) {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'chat', label: 'Chat with Data', icon: MessageSquare },
    { id: 'predictions', label: 'Predictions', icon: TrendingUp },
  ];

  return (
    <aside className="border-b border-white/10 bg-white/[0.04] backdrop-blur-xl lg:min-h-screen lg:w-64 lg:shrink-0 lg:border-b-0 lg:border-r">
      <div className="p-4 sm:p-5 lg:sticky lg:top-0 lg:flex lg:min-h-screen lg:flex-col lg:p-6">
        <h1 className="mb-4 text-lg font-bold tracking-wider text-slate-100 lg:mb-10 lg:text-xl">
          SALES <span className="text-indigo-400">AI</span>
        </h1>
        
        <nav className="flex gap-2 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = page === item.id;
            
            return (
              <button
                key={item.id}
                onClick={() => setPage(item.id)}
                className={`flex shrink-0 items-center gap-2 rounded-xl px-3 py-2.5 transition-all duration-200 sm:gap-3 sm:px-4 lg:w-full ${
                  isActive 
                    ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 shadow-[0_0_15px_rgba(99,102,241,0.1)]' 
                    : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
                }`}
              >
                <Icon className="w-5 h-5" />
                <span className="whitespace-nowrap text-xs font-medium sm:text-sm">{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </aside>
  )
}