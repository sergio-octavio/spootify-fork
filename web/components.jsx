// Spootify UI primitives
const { useState, useEffect, useRef, useMemo, useCallback, Fragment } = React;

// ─── Icons ─────────────────────────────────────────────────────────
const Icon = {
  play: (s=16, c='#000') => <svg width={s} height={s} viewBox="0 0 16 16" fill={c}><path d="M3 2.5v11a.5.5 0 00.77.42l9-5.5a.5.5 0 000-.84l-9-5.5A.5.5 0 003 2.5z"/></svg>,
  pause: (s=16, c='#000') => <svg width={s} height={s} viewBox="0 0 16 16" fill={c}><rect x="3.5" y="2" width="3" height="12" rx="0.8"/><rect x="9.5" y="2" width="3" height="12" rx="0.8"/></svg>,
  next: (s=18, c='#fff') => <svg width={s} height={s} viewBox="0 0 18 18" fill={c}><path d="M3 2.5v13a.5.5 0 00.78.42L14 9.5a.5.5 0 000-.84L3.78 2.08A.5.5 0 003 2.5z"/><rect x="14.4" y="2.5" width="1.6" height="13" rx="0.5"/></svg>,
  prev: (s=18, c='#fff') => <svg width={s} height={s} viewBox="0 0 18 18" fill={c}><rect x="2.4" y="2.5" width="1.6" height="13" rx="0.5"/><path d="M15 2.5v13a.5.5 0 01-.78.42L4.5 9.42a.5.5 0 010-.84L14.22 2.08A.5.5 0 0115 2.5z"/></svg>,
  heart: (s=22, c='#fff', filled=false) => filled
    ? <svg width={s} height={s} viewBox="0 0 24 24" fill={c}><path d="M12 21s-7.5-4.6-10-9.3C.3 8.4 2.2 4 6.2 4c2.1 0 3.7 1 4.8 2.6C12.1 5 13.7 4 15.8 4c4 0 5.9 4.4 4.2 7.7C19.5 16.4 12 21 12 21z"/></svg>
    : <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2"><path d="M12 20.5S4.5 16 2.4 11.5C.8 8 2.7 4.5 6 4.5c2.1 0 3.8 1.1 4.7 2.7C11.5 5.6 13.2 4.5 15.3 4.5c3.3 0 5.2 3.5 3.6 7-2.1 4.5-6.9 9-6.9 9z" strokeLinejoin="round"/></svg>,
  heartSm: (s=16, c='#D4FF3D') => <svg width={s} height={s} viewBox="0 0 24 24" fill={c}><path d="M12 21s-7.5-4.6-10-9.3C.3 8.4 2.2 4 6.2 4c2.1 0 3.7 1 4.8 2.6C12.1 5 13.7 4 15.8 4c4 0 5.9 4.4 4.2 7.7C19.5 16.4 12 21 12 21z"/></svg>,
  dots: (s=18, c='#fff') => <svg width={s} height={s} viewBox="0 0 18 4" fill={c}><circle cx="2" cy="2" r="2"/><circle cx="9" cy="2" r="2"/><circle cx="16" cy="2" r="2"/></svg>,
  dotsV: (s=18, c='rgba(255,255,255,0.6)') => <svg width={s} height={s} viewBox="0 0 4 18" fill={c}><circle cx="2" cy="2" r="2"/><circle cx="2" cy="9" r="2"/><circle cx="2" cy="16" r="2"/></svg>,
  shuffle: (s=18, c='#fff') => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 3h5v5"/><path d="M4 20L21 3"/><path d="M21 16v5h-5"/><path d="M15 15l6 6"/><path d="M4 4l5 5"/></svg>,
  repeat: (s=18, c='#fff') => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 1l4 4-4 4"/><path d="M3 11V9a4 4 0 014-4h14"/><path d="M7 23l-4-4 4-4"/><path d="M21 13v2a4 4 0 01-4 4H3"/></svg>,
  queue: (s=18, c='#fff') => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18M3 12h18M3 18h12"/></svg>,
  chevDown: (s=18, c='#fff') => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 9l6 6 6-6"/></svg>,
  chevLeft: (s=18, c='#fff') => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 18l-6-6 6-6"/></svg>,
  chevRight: (s=12, c='rgba(255,255,255,0.35)') => <svg width={s} height={s*1.5} viewBox="0 0 8 12" fill="none" stroke={c} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M1 1l5 5-5 5"/></svg>,
  search: (s=18, c='#fff') => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg>,
  plus: (s=18, c='#fff') => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2.2" strokeLinecap="round"><path d="M12 5v14M5 12h14"/></svg>,
  check: (s=16, c='#000') => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12l5 5L20 7"/></svg>,
  pin: (s=12, c='#D4FF3D') => <svg width={s} height={s} viewBox="0 0 24 24" fill={c}><path d="M14 2l8 8-5 1-4 4-1 6-5-5-5 5 1-6 5-5 1-4 5-5z"/></svg>,
  bars: (s=14, c='#D4FF3D') => (
    <svg width={s} height={s} viewBox="0 0 14 14">
      <rect x="1"  y="4" width="2" height="6" rx="1" fill={c}>
        <animate attributeName="height" values="6;10;3;8;6" dur="1s" repeatCount="indefinite"/>
        <animate attributeName="y"      values="4;2;5;3;4"   dur="1s" repeatCount="indefinite"/>
      </rect>
      <rect x="5"  y="2" width="2" height="10" rx="1" fill={c}>
        <animate attributeName="height" values="10;4;8;3;10" dur="1s" repeatCount="indefinite"/>
        <animate attributeName="y"      values="2;7;3;8;2"    dur="1s" repeatCount="indefinite"/>
      </rect>
      <rect x="9"  y="3" width="2" height="8" rx="1" fill={c}>
        <animate attributeName="height" values="8;3;10;5;8"  dur="1s" repeatCount="indefinite"/>
        <animate attributeName="y"      values="3;8;2;6;3"    dur="1s" repeatCount="indefinite"/>
      </rect>
    </svg>
  ),
  library: (s=22, c='#fff') => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="4" height="16" rx="1"/><rect x="10" y="4" width="4" height="16" rx="1"/><path d="M18 4l3 .7-3 14.5-3-.7z"/></svg>,
  mic: (s=22, c='#fff') => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 11a7 7 0 0014 0"/><path d="M12 18v4M8 22h8"/></svg>,
};

// ─── Cover (generative gradient + optional real image overlay) ───
// `coverUrl` (opcional): si se pasa, pinta la imagen encima del gradiente
// una vez cargada. El gradiente sigue sirviendo como skeleton / fallback.
function Cover({ seed, size = 48, radius = 6, accent = '#D4FF3D', label, coverUrl, children }) {
  const bg = coverGradient(seed, accent);
  const h = hashHue(seed);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => { setLoaded(false); }, [coverUrl]);
  return (
    <div style={{
      width: size, height: size, borderRadius: radius, background: bg,
      position: 'relative', overflow: 'hidden', flexShrink: 0,
      boxShadow: '0 2px 6px rgba(0,0,0,0.3), inset 0 0 0 0.5px rgba(255,255,255,0.06)',
    }}>
      {/* diagonal tonal band */}
      <div style={{
        position: 'absolute', inset: 0,
        background: `linear-gradient(${h % 180}deg, transparent 40%, rgba(255,255,255,0.04) 50%, transparent 60%)`,
      }} />
      {coverUrl && (
        <img
          src={coverUrl}
          alt=""
          onLoad={() => setLoaded(true)}
          onError={() => setLoaded(false)}
          draggable={false}
          style={{
            position: 'absolute', inset: 0, width: '100%', height: '100%',
            objectFit: 'cover', display: 'block',
            opacity: loaded ? 1 : 0,
            transition: 'opacity 180ms ease',
          }}
        />
      )}
      {label !== undefined && !loaded && (
        <div style={{
          position: 'absolute', inset: 0, display: 'flex', alignItems: 'flex-end',
          padding: size > 100 ? 14 : 6,
          fontFamily: 'ui-monospace, Menlo, monospace',
          fontSize: Math.max(8, size * 0.08), color: 'rgba(255,255,255,0.4)',
          letterSpacing: 0.5, textTransform: 'uppercase',
        }}>{label}</div>
      )}
      {children}
    </div>
  );
}

// ─── Artist avatar — monochrome with lime ring option ─────────────
function ArtistAvatar({ seed, size = 56, accent = '#D4FF3D', initials }) {
  const h = hashHue(seed);
  const bg = `conic-gradient(from ${h}deg at 30% 30%, oklch(32% 0.02 ${h}), oklch(22% 0.01 ${(h+120)%360}), oklch(38% 0.025 ${(h+240)%360}), oklch(32% 0.02 ${h}))`;
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%', background: bg,
      display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
      fontFamily: '"Space Grotesk", -apple-system, system-ui', fontWeight: 600,
      fontSize: size * 0.35, color: 'rgba(255,255,255,0.55)',
      boxShadow: 'inset 0 0 0 0.5px rgba(255,255,255,0.08)',
    }}>{initials}</div>
  );
}

// ─── Song row ─────────────────────────────────────────────────────
function SongRow({ song, artist, index, isPlaying, isCurrent, liked, onPlay, onLike, onMenu, showArt = true, accent = '#D4FF3D', density = 'comfortable' }) {
  const pad = density === 'compact' ? '6px 16px' : density === 'spacious' ? '12px 16px' : '8px 16px';
  const art = density === 'compact' ? 40 : 48;
  return (
    <div onClick={onPlay} style={{
      display: 'flex', alignItems: 'center', gap: 12, padding: pad, cursor: 'pointer',
      userSelect: 'none',
    }}>
      {showArt && (
        <Cover seed={song.album + song.artistId} coverUrl={song.coverUrl} size={art} />
      )}
      {!showArt && (
        <div style={{ width: 22, textAlign: 'center', color: isCurrent ? accent : 'rgba(255,255,255,0.45)', fontSize: 14, fontVariantNumeric: 'tabular-nums' }}>
          {isCurrent && isPlaying ? Icon.bars(14, accent) : String(index + 1).padStart(2, '0')}
        </div>
      )}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          color: isCurrent ? accent : '#fff', fontSize: 15, fontWeight: 500,
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          letterSpacing: -0.2,
        }}>{song.title}</div>
        <div style={{
          color: 'rgba(255,255,255,0.5)', fontSize: 13, marginTop: 2,
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>{artist?.name}{song.album ? ` · ${song.album}` : ''}</div>
      </div>
      <button onClick={(e) => { e.stopPropagation(); onLike?.(); }} style={{
        background: 'none', border: 'none', padding: 6, cursor: 'pointer',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {liked ? Icon.heartSm(16, accent) : Icon.heart(16, 'rgba(255,255,255,0.45)')}
      </button>
      <button onClick={(e) => { e.stopPropagation(); onMenu?.(); }} style={{
        background: 'none', border: 'none', padding: 6, cursor: 'pointer',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {Icon.dotsV(14, 'rgba(255,255,255,0.4)')}
      </button>
    </div>
  );
}

// ─── Tabs (bottom) ────────────────────────────────────────────────
function BottomTabs({ tab, onChange, accent }) {
  const items = [
    { id: 'library',  label: 'Biblioteca', icon: Icon.library },
    { id: 'artists',  label: 'Artistas',   icon: Icon.mic },
    { id: 'search',   label: 'Buscar',     icon: Icon.search },
  ];
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-around',
      padding: '8px 0 0', background: 'rgba(10,10,10,0.92)',
      backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)',
      borderTop: '0.5px solid rgba(255,255,255,0.06)',
    }}>
      {items.map(it => {
        const active = tab === it.id;
        const c = active ? accent : 'rgba(255,255,255,0.5)';
        return (
          <button key={it.id} onClick={() => onChange(it.id)} style={{
            flex: 1, background: 'none', border: 'none', padding: '6px 0 4px',
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3,
            cursor: 'pointer', color: c,
          }}>
            {it.icon(22, c)}
            <span style={{ fontSize: 10, fontWeight: 500, letterSpacing: 0.2 }}>{it.label}</span>
          </button>
        );
      })}
    </div>
  );
}

Object.assign(window, { Icon, Cover, ArtistAvatar, SongRow, BottomTabs, BottomSheet });

// ─── Bottom Sheet (animated slide-up) ─────────────────────────────
// Usage: always mount conditionally in parent; sheet animates IN on mount.
// When user dismisses, sheet animates OUT, then calls onClose().
function BottomSheet({ onClose, children, maxHeight, zIndex = 300 }) {
  const [visible, setVisible] = useState(false);
  const [closing, setClosing] = useState(false);
  useEffect(() => {
    const r = requestAnimationFrame(() => requestAnimationFrame(() => setVisible(true)));
    return () => cancelAnimationFrame(r);
  }, []);
  const close = useCallback(() => {
    if (closing) return;
    setClosing(true);
    setVisible(false);
    setTimeout(() => onClose?.(), 260);
  }, [onClose, closing]);
  return (
    <div onClick={close} style={{
      position: 'absolute', inset: 0, zIndex,
      background: visible ? 'rgba(0,0,0,0.6)' : 'rgba(0,0,0,0)',
      backdropFilter: visible ? 'blur(6px)' : 'blur(0px)',
      WebkitBackdropFilter: visible ? 'blur(6px)' : 'blur(0px)',
      transition: 'background 240ms ease, backdrop-filter 240ms ease',
      display: 'flex', alignItems: 'flex-end',
    }}>
      <div onClick={(e) => e.stopPropagation()} style={{
        width: '100%', background: '#1a1a1a', borderRadius: '20px 20px 0 0',
        maxHeight: maxHeight || '84%', display: 'flex', flexDirection: 'column',
        transform: visible ? 'translateY(0)' : 'translateY(100%)',
        transition: 'transform 280ms cubic-bezier(0.22, 1, 0.36, 1)',
        boxShadow: '0 -10px 40px rgba(0,0,0,0.5)',
      }}>
        <div style={{ width: 36, height: 4, borderRadius: 4, background: 'rgba(255,255,255,0.2)', margin: '10px auto 6px', flexShrink: 0 }} />
        {typeof children === 'function' ? children(close) : children}
      </div>
    </div>
  );
}
