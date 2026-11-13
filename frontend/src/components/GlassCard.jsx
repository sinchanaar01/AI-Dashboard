export default function GlassCard({ children, className = "" }) {
  return (
    <div className={`relative rounded-2xl bg-white/[0.04] backdrop-blur-xl border border-white/10 p-6 shadow-2xl transition-all duration-300 hover:border-white/20 ${className}`}>
      {children}
    </div>
  );
}