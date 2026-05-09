// Spootify screens — with search, sort, swipe, context menus

// ─── Shared top bar ────────────────────────────────────────────
function TopBar({ title, onBack, right, accent, transparent }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '8px 12px', gap: 8,
      background: transparent ? 'transparent' : 'rgba(10,10,10,0.7)',
      backdropFilter: transparent ? undefined : 'blur(16px)',
      WebkitBackdropFilter: transparent ? undefined : 'blur(16px)',
      position: 'sticky', top: 44, zIndex: 5,
    }}>
      {onBack ? (
        <button onClick={onBack} style={{
          width: 36, height: 36, borderRadius: 18, border: 'none',
          background: transparent ? 'rgba(0,0,0,0.65)' : 'rgba(255,255,255,0.08)',
          display: 'flex',
          alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
          backdropFilter: transparent ? 'blur(10px)' : undefined,
          WebkitBackdropFilter: transparent ? 'blur(10px)' : undefined,
          boxShadow: transparent ? 'inset 0 0 0 0.5px rgba(255,255,255,0.12)' : undefined,
        }}>{Icon.chevLeft(18, '#fff')}</button>
      ) : <div style={{ width: 36 }} />}
      <div style={{
        flex: 1, textAlign: 'center', color: '#fff', fontSize: 15, fontWeight: 600,
        letterSpacing: -0.2,
      }}>{title}</div>
      {right || <div style={{ width: 36 }} />}
    </div>
  );
}

const iconBtn = {
  width: 36, height: 36, borderRadius: 18, border: 'none',
  background: 'rgba(255,255,255,0.08)', color: '#fff',
  display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
};

// ─── SearchBar (embedded) ──────────────────────────────────────
function SearchBar({ value, onChange, placeholder }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8, padding: '9px 12px',
      borderRadius: 10, background: 'rgba(255,255,255,0.08)',
    }}>
      {Icon.search(15, 'rgba(255,255,255,0.5)')}
      <input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} style={{
        flex: 1, background: 'transparent', border: 'none', outline: 'none',
        color: '#fff', fontSize: 14, fontFamily: 'inherit', minWidth: 0,
      }} />
      {value && (
        <button onClick={() => onChange('')} style={{
          background: 'none', border: 'none', padding: 2, cursor: 'pointer',
          color: 'rgba(255,255,255,0.5)', fontSize: 18, lineHeight: 1,
        }}>×</button>
      )}
    </div>
  );
}

// ─── SwipeableRow ──────────────────────────────────────────────
// Drag right (positive x) → action right (e.g. add to queue)
// Drag left (negative x) → action left (e.g. add to playlist)
function SwipeableRow({ children, onSwipeRight, onSwipeLeft, rightBg = '#D4FF3D', leftBg = '#3D9DFF', rightLabel = 'A la cola', leftLabel = 'A playlist', rightIcon, leftIcon }) {
  const [dx, setDx] = useState(0);
  const [flash, setFlash] = useState(null); // 'r' | 'l'
  const start = useRef(null);
  const active = useRef(false);
  const THRESHOLD = 72;

  const handleStart = (x, y) => { start.current = { x, y }; active.current = false; };
  const handleMove = (x, y) => {
    if (!start.current) return;
    const dxRaw = x - start.current.x;
    const dyRaw = y - start.current.y;
    if (!active.current) {
      if (Math.abs(dxRaw) < 6) return;
      if (Math.abs(dyRaw) > Math.abs(dxRaw)) { start.current = null; return; }
      active.current = true;
    }
    // dampen beyond threshold*2
    const clamped = Math.max(-160, Math.min(160, dxRaw));
    setDx(clamped);
  };
  const handleEnd = () => {
    if (!active.current) { setDx(0); start.current = null; return; }
    if (dx >= THRESHOLD && onSwipeRight) { setFlash('r'); onSwipeRight(); }
    else if (dx <= -THRESHOLD && onSwipeLeft) { setFlash('l'); onSwipeLeft(); }
    setDx(0);
    start.current = null;
    active.current = false;
    if (flash) setTimeout(() => setFlash(null), 400);
  };

  useEffect(() => {
    if (flash) { const t = setTimeout(() => setFlash(null), 400); return () => clearTimeout(t); }
  }, [flash]);

  const progress = Math.min(1, Math.abs(dx) / THRESHOLD);

  return (
    <div style={{ position: 'relative', overflow: 'hidden' }}>
      {/* Right action (revealed when dragging right) */}
      <div style={{
        position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
        justifyContent: 'flex-start', paddingLeft: 20, gap: 10,
        background: rightBg, opacity: dx > 0 || flash === 'r' ? 1 : 0,
        transition: flash === 'r' ? 'opacity 0.2s' : undefined,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#000', fontWeight: 700, fontSize: 13, transform: `scale(${0.85 + progress * 0.15})`, transition: 'transform 0.1s' }}>
          {rightIcon || Icon.queue(16, '#000')}
          <span>{rightLabel}</span>
        </div>
      </div>
      {/* Left action (revealed when dragging left) */}
      <div style={{
        position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
        justifyContent: 'flex-end', paddingRight: 20, gap: 10,
        background: leftBg, opacity: dx < 0 || flash === 'l' ? 1 : 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#fff', fontWeight: 700, fontSize: 13, transform: `scale(${0.85 + progress * 0.15})`, transition: 'transform 0.1s' }}>
          {leftIcon || Icon.plus(16, '#fff')}
          <span>{leftLabel}</span>
        </div>
      </div>
      {/* Foreground row */}
      <div
        onTouchStart={(e) => handleStart(e.touches[0].clientX, e.touches[0].clientY)}
        onTouchMove={(e) => handleMove(e.touches[0].clientX, e.touches[0].clientY)}
        onTouchEnd={handleEnd}
        onMouseDown={(e) => { handleStart(e.clientX, e.clientY); e.currentTarget.setPointerCapture?.(e.pointerId); }}
        onMouseMove={(e) => { if (start.current && e.buttons === 1) handleMove(e.clientX, e.clientY); }}
        onMouseUp={handleEnd}
        onMouseLeave={() => { if (start.current) handleEnd(); }}
        style={{
          transform: `translateX(${dx}px)`,
          transition: active.current ? 'none' : 'transform 0.25s cubic-bezier(.2,.9,.3,1)',
          background: '#0a0a0a', position: 'relative',
        }}>
        {children}
      </div>
    </div>
  );
}

// ─── BIBLIOTECA ────────────────────────────────────────────────
function LibraryScreen({ playlists, albums = [], onOpenPlaylist, onOpenAlbum, onCreatePlaylist, accent, density }) {
  const [filter, setFilter] = useState('Todas');
  const chips = ['Todas', 'Playlists', 'Álbumes'];
  const showPlaylists = filter === 'Todas' || filter === 'Playlists';
  const showAlbums = filter === 'Todas' || filter === 'Álbumes';
  const summary =
    filter === 'Todas' ? `${playlists.length} playlists · ${albums.length} álbumes`
    : filter === 'Playlists' ? `${playlists.length} playlists`
    : `${albums.length} álbumes`;
  return (
    <div style={{ paddingBottom: 16 }}>
      <div style={{ padding: '14px 16px 10px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 32, height: 32, borderRadius: '50%',
            background: `linear-gradient(135deg, ${accent}, oklch(70% 0.14 140))`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#000', fontWeight: 700, fontSize: 14,
          }}>R</div>
          <h1 style={{ margin: 0, color: '#fff', fontSize: 24, fontWeight: 700, letterSpacing: -0.5 }}>Tu biblioteca</h1>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button style={iconBtn} onClick={onCreatePlaylist}>{Icon.plus(18)}</button>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 8, padding: '4px 16px 10px' }}>
        {chips.map(c => {
          const active = filter === c;
          return (
            <button key={c} onClick={() => setFilter(c)} style={{
              padding: '6px 12px', borderRadius: 999, border: 'none', cursor: 'pointer',
              background: active ? accent : 'rgba(255,255,255,0.08)',
              color: active ? '#000' : '#fff', fontSize: 13, fontWeight: 500,
            }}>{c}</button>
          );
        })}
      </div>
      <div style={{ padding: '6px 18px 10px' }}>
        <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)' }}>{summary}</span>
      </div>
      {showPlaylists && playlists.map(pl => (
        <PlaylistRow key={pl.id} playlist={pl} onClick={() => onOpenPlaylist(pl.id)} accent={accent} density={density} />
      ))}
      {showAlbums && albums.map(al => (
        <AlbumRow key={al.id} album={al} onClick={() => onOpenAlbum && onOpenAlbum(al.id)} accent={accent} density={density} />
      ))}
    </div>
  );
}

function AlbumRow({ album, onClick, accent, density }) {
  const size = density === 'compact' ? 52 : density === 'spacious' ? 68 : 60;
  return (
    <div onClick={onClick} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 16px', cursor: 'pointer' }}>
      <Cover seed={album.title + (album.artistId || '')} coverUrl={album.coverUrl} size={size} radius={6} accent={accent} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ color: '#fff', fontSize: 15, fontWeight: 600, letterSpacing: -0.2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{album.title}</div>
        <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13, marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          Álbum · {album.artistName || '?'} · {album.items?.length || 0}
        </div>
      </div>
    </div>
  );
}

function PlaylistRow({ playlist, onClick, accent, density }) {
  const size = density === 'compact' ? 52 : density === 'spacious' ? 68 : 60;
  const isSaved = playlist.id === 'saved';
  return (
    <div onClick={onClick} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 16px', cursor: 'pointer' }}>
      {isSaved ? (
        <div style={{
          width: size, height: size, borderRadius: 8,
          background: `linear-gradient(135deg, ${accent} 0%, oklch(55% 0.14 145) 100%)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
        }}>{Icon.heart(28, '#0a0a0a', true)}</div>
      ) : (
        <Cover seed={playlist.coverSeed || playlist.title} coverUrl={playlist.coverUrl} size={size} radius={8} accent={accent} />
      )}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ color: '#fff', fontSize: 15, fontWeight: 600, letterSpacing: -0.2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{playlist.title}</div>
        <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13, marginTop: 2, display: 'flex', alignItems: 'center', gap: 6 }}>
          {playlist.pinned && Icon.pin(11, accent)}
          <span>Playlist{playlist.subtitle ? ` · ${playlist.subtitle}` : ''} · {playlist.items.length}</span>
        </div>
      </div>
    </div>
  );
}

// ─── PLAYLIST DETAIL ───────────────────────────────────────────
const SORT_OPTIONS = [
  { id: 'custom', label: 'Personalizado' },
  { id: 'added', label: 'Fecha de inclusión' },
  { id: 'title', label: 'Nombre' },
  { id: 'artist', label: 'Artista' },
];

function PlaylistScreen({ playlist, songs, items, artists, likedSet, onBack, onPlaySong, currentId, isPlaying, onLike, onShuffle, shuffleOn, accent, density, onSongMenu, onSwipeQueue, onSwipeAddPlaylist, onEdit }) {
  const artistsById = useMemo(() => Object.fromEntries(artists.map(a => [a.id, a])), [artists]);
  const isSaved = playlist.id === 'saved';
  const [scrollY, setScrollY] = useState(0);
  const [q, setQ] = useState('');
  const [sortBy, setSortBy] = useState('added');
  const [sortDir, setSortDir] = useState('desc'); // desc = newest/Z-A first
  const [sortOpen, setSortOpen] = useState(false);

  // Map songId → addedAt from items
  const addedMap = useMemo(() => Object.fromEntries((items || []).map(it => [it.id, it.addedAt || 0])), [items]);

  // Filter
  const filtered = useMemo(() => {
    const qq = q.trim().toLowerCase();
    if (!qq) return songs;
    return songs.filter(s => {
      const a = artistsById[s.artistId]?.name || '';
      return s.title.toLowerCase().includes(qq) ||
             s.album.toLowerCase().includes(qq) ||
             a.toLowerCase().includes(qq);
    });
  }, [q, songs, artistsById]);

  // Sort (custom = manual playlist order, preserve items[] sequence)
  const sorted = useMemo(() => {
    if (sortBy === 'custom') {
      const byId = Object.fromEntries(filtered.map(s => [s.id, s]));
      const ordered = (items || []).map(it => byId[it.id]).filter(Boolean);
      return sortDir === 'asc' ? ordered.slice().reverse() : ordered;
    }
    const arr = [...filtered];
    const cmp = (a, b) => {
      let v = 0;
      if (sortBy === 'title') v = a.title.localeCompare(b.title, 'es');
      else if (sortBy === 'artist') v = (artistsById[a.artistId]?.name || '').localeCompare(artistsById[b.artistId]?.name || '', 'es');
      else v = (addedMap[a.id] || 0) - (addedMap[b.id] || 0);
      return sortDir === 'asc' ? v : -v;
    };
    arr.sort(cmp);
    return arr;
  }, [filtered, sortBy, sortDir, artistsById, addedMap, items]);

  const total = totalDuration(songs);

  return (
    <div onScroll={(e) => setScrollY(e.target.scrollTop)} style={{ position: 'absolute', inset: 0, overflowY: 'auto' }}>
      {/* Hero */}
      <div style={{
        position: 'relative', height: 280, marginTop: -44,
        background: isSaved
          ? `linear-gradient(180deg, ${accent}33 0%, transparent 100%)`
          : `radial-gradient(at 50% 0%, oklch(40% 0.05 ${hashHue(playlist.coverSeed || playlist.title)}) 0%, transparent 70%)`,
      }}>
        <TopBar onBack={onBack} title={scrollY > 140 ? playlist.title : ''} accent={accent} transparent={scrollY < 140}
          right={<button onClick={onEdit} style={iconBtn}>{Icon.dots(18)}</button>} />
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '12px 24px 20px' }}>
          {isSaved ? (
            <div style={{
              width: 168, height: 168, borderRadius: 12,
              background: `linear-gradient(135deg, ${accent} 0%, oklch(55% 0.14 145) 100%)`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 16px 40px rgba(0,0,0,0.5)',
            }}>{Icon.heart(76, '#0a0a0a', true)}</div>
          ) : (
            <Cover seed={playlist.coverSeed || playlist.title} coverUrl={playlist.coverUrl} size={168} radius={12} accent={accent} label={playlist.title.slice(0,10)} />
          )}
        </div>
      </div>

      {/* Title + meta */}
      <div style={{ padding: '0 16px 12px' }}>
        <h1 style={{ margin: 0, color: '#fff', fontSize: 28, fontWeight: 700, letterSpacing: -0.5 }}>{playlist.title}</h1>
        <div style={{ color: 'rgba(255,255,255,0.55)', fontSize: 13, marginTop: 6 }}>
          {playlist.subtitle || 'Tu lista'} · {songs.length} canciones · {fmtTotal(total)}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 14 }}>
          <div style={{ display: 'flex', gap: 8 }}>
            {isSaved && (
              <div style={{ width: 36, height: 36, borderRadius: 18, background: accent, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{Icon.heart(18, '#000', true)}</div>
            )}
            <button onClick={onShuffle} style={{
              ...iconBtn, width: 36, height: 36,
              background: shuffleOn ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.08)',
            }}>{Icon.shuffle(16, shuffleOn ? accent : 'rgba(255,255,255,0.8)')}</button>
          </div>
          <button onClick={() => sorted[0] && onPlaySong(sorted[0].id, sorted.map(s => s.id))} style={{
            width: 52, height: 52, borderRadius: '50%', border: 'none', background: accent, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: `0 6px 20px ${accent}60`,
          }}>{Icon.play(20, '#000')}</button>
        </div>
      </div>

      {/* Search + Sort */}
      <div style={{ padding: '4px 16px 8px' }}>
        <SearchBar value={q} onChange={setQ} placeholder="Buscar en canción, álbum o artista" />
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 10, position: 'relative' }}>
          <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)' }}>{sorted.length} de {songs.length}</span>
          <button onClick={() => setSortOpen(o => !o)} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: accent, fontSize: 12, fontWeight: 600, display: 'flex', gap: 4, alignItems: 'center',
          }}>
            {SORT_OPTIONS.find(s => s.id === sortBy).label} {sortDir === 'asc' ? '↑' : '↓'}
          </button>
          {sortOpen && (
            <div style={{
              position: 'absolute', top: 22, right: 0, zIndex: 10,
              background: '#1e1e1e', borderRadius: 10, padding: 6, minWidth: 200,
              boxShadow: '0 10px 30px rgba(0,0,0,0.5)', border: '0.5px solid rgba(255,255,255,0.08)',
            }}>
              {SORT_OPTIONS.map(opt => (
                <button key={opt.id} onClick={() => { setSortBy(opt.id); setSortOpen(false); }} style={{
                  width: '100%', textAlign: 'left', padding: '9px 10px', borderRadius: 6,
                  background: sortBy === opt.id ? 'rgba(255,255,255,0.06)' : 'none', border: 'none', cursor: 'pointer',
                  color: sortBy === opt.id ? accent : '#fff', fontSize: 13, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                }}>
                  <span>{opt.label}</span>
                  {sortBy === opt.id && <span style={{ color: accent }}>✓</span>}
                </button>
              ))}
              <div style={{ height: 1, background: 'rgba(255,255,255,0.08)', margin: '4px 0' }} />
              <button onClick={() => { setSortDir(d => d === 'asc' ? 'desc' : 'asc'); setSortOpen(false); }} style={{
                width: '100%', textAlign: 'left', padding: '9px 10px', borderRadius: 6,
                background: 'none', border: 'none', cursor: 'pointer',
                color: '#fff', fontSize: 13, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              }}>
                <span>Orden</span>
                <span style={{ color: 'rgba(255,255,255,0.6)' }}>{sortDir === 'asc' ? 'Ascendente ↑' : 'Descendente ↓'}</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Song list */}
      <div style={{ paddingBottom: 140 }}>
        {sorted.map((s, i) => (
          <SwipeableRow key={s.id}
            onSwipeRight={() => onSwipeQueue?.(s.id)}
            onSwipeLeft={() => onSwipeAddPlaylist?.(s.id)}
            rightBg={accent} leftBg="rgba(60,60,60,0.9)"
            rightLabel="A la cola" leftLabel="A playlist"
            rightIcon={Icon.queue(16, '#000')} leftIcon={Icon.plus(16, '#fff')}
          >
            <SongRow
              song={s} artist={artistsById[s.artistId]} index={i}
              isCurrent={currentId === s.id} isPlaying={isPlaying && currentId === s.id}
              liked={likedSet.has(s.id)}
              onPlay={() => onPlaySong(s.id, sorted.map(x => x.id))}
              onLike={() => onLike(s.id)}
              onMenu={() => onSongMenu?.(s)}
              accent={accent} density={density} showArt={false}
            />
          </SwipeableRow>
        ))}
        {sorted.length === 0 && (
          <div style={{ padding: 32, textAlign: 'center', color: 'rgba(255,255,255,0.4)', fontSize: 13 }}>
            Sin resultados
          </div>
        )}
      </div>
    </div>
  );
}

// ─── ARTISTS LIST ──────────────────────────────────────────────
function ArtistsScreen({ artists, songs, likedSet, playlists, onOpenArtist, accent, density }) {
  const libraryArtistIds = useMemo(() => {
    const ids = new Set();
    playlists.forEach(pl => pl.items.forEach(it => {
      const s = songs.find(x => x.id === it.id);
      if (s) ids.add(s.artistId);
    }));
    likedSet.forEach(sid => {
      const s = songs.find(x => x.id === sid);
      if (s) ids.add(s.artistId);
    });
    return [...ids];
  }, [playlists, likedSet, songs]);

  const listed = artists.filter(a => libraryArtistIds.includes(a.id));

  return (
    <div style={{ paddingBottom: 140 }}>
      <div style={{ padding: '14px 16px 10px' }}>
        <h1 style={{ margin: 0, color: '#fff', fontSize: 24, fontWeight: 700, letterSpacing: -0.5 }}>Artistas</h1>
        <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13, marginTop: 4 }}>{listed.length} en tu biblioteca</div>
      </div>
      {listed.map(a => {
        const count = songs.filter(s => s.artistId === a.id).length;
        return (
          <div key={a.id} onClick={() => onOpenArtist(a.id)} style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '10px 16px', cursor: 'pointer' }}>
            <ArtistAvatar seed={a.name} size={56} accent={accent} initials={a.name.split(' ').map(w => w[0]).slice(0,2).join('')} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ color: '#fff', fontSize: 15, fontWeight: 600, letterSpacing: -0.2 }}>{a.name}</div>
              <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13, marginTop: 2 }}>Artista · {count} canción{count !== 1 ? 'es' : ''}</div>
            </div>
            {Icon.chevRight(10)}
          </div>
        );
      })}
    </div>
  );
}

// ─── ARTIST DETAIL ─────────────────────────────────────────────
function ArtistScreen({ artist, songs, artists, likedSet, onBack, onPlaySong, onLike, currentId, isPlaying, accent, density, onSongMenu }) {
  const artistsById = useMemo(() => Object.fromEntries(artists.map(a => [a.id, a])), [artists]);
  const [scrollY, setScrollY] = useState(0);

  const albums = useMemo(() => {
    const m = new Map();
    songs.forEach(s => {
      if (!m.has(s.album)) m.set(s.album, []);
      m.get(s.album).push(s);
    });
    return [...m.entries()];
  }, [songs]);

  return (
    <div onScroll={(e) => setScrollY(e.target.scrollTop)} style={{ position: 'absolute', inset: 0, overflowY: 'auto' }}>
      <div style={{
        position: 'relative', height: 280, marginTop: -44,
        background: `radial-gradient(at 50% 30%, oklch(35% 0.04 ${hashHue(artist.name)}) 0%, #0a0a0a 80%)`,
        overflow: 'hidden',
      }}>
        <TopBar onBack={onBack} title={scrollY > 180 ? artist.name : ''} transparent={scrollY < 180}
          right={<button style={iconBtn}>{Icon.dots(18)}</button>} />
        <div style={{ position: 'absolute', bottom: 20, left: 20, right: 20 }}>
          <h1 style={{ margin: 0, color: '#fff', fontSize: 36, fontWeight: 700, letterSpacing: -0.8 }}>{artist.name}</h1>
          <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: 12, marginTop: 4, textTransform: 'uppercase', letterSpacing: 1 }}>
            {artist.genre} · {artist.monthly.toLocaleString('es')} oyentes mensuales
          </div>
        </div>
        <div style={{
          position: 'absolute', top: 40, right: -20, opacity: 0.08,
          fontSize: 260, fontWeight: 900, color: '#fff', lineHeight: 1,
        }}>{artist.name[0]}</div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 16px' }}>
        <button style={{ ...iconBtn, padding: '0 14px', width: 'auto', height: 36 }}>
          <span style={{ fontSize: 13, fontWeight: 600 }}>Seguir</span>
        </button>
        <div style={{ display: 'flex', gap: 8 }}>
          <button style={{ ...iconBtn, width: 36, height: 36 }}>{Icon.shuffle(16, 'rgba(255,255,255,0.8)')}</button>
          <button onClick={() => songs[0] && onPlaySong(songs[0].id, songs.map(s => s.id))} style={{
            width: 48, height: 48, borderRadius: '50%', border: 'none', background: accent, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: `0 6px 20px ${accent}50`,
          }}>{Icon.play(18, '#000')}</button>
        </div>
      </div>

      <div style={{ padding: '0 16px 8px' }}>
        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', textTransform: 'uppercase', letterSpacing: 1.5, fontWeight: 600, marginBottom: 6 }}>En tu biblioteca</div>
      </div>
      <div style={{ paddingBottom: 140 }}>
        {albums.map(([album, albumSongs]) => (
          <div key={album} style={{ marginTop: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 16px' }}>
              <Cover seed={album + artist.id} size={36} radius={4} accent={accent} />
              <div>
                <div style={{ color: '#fff', fontSize: 13, fontWeight: 600 }}>{album}</div>
                <div style={{ color: 'rgba(255,255,255,0.45)', fontSize: 11 }}>Álbum · {albumSongs.length} canciones</div>
              </div>
            </div>
            {albumSongs.map((s, i) => (
              <SongRow
                key={s.id} song={s} artist={artistsById[s.artistId]} index={i}
                isCurrent={currentId === s.id} isPlaying={isPlaying && currentId === s.id}
                liked={likedSet.has(s.id)}
                onPlay={() => onPlaySong(s.id, albumSongs.map(x => x.id))}
                onLike={() => onLike(s.id)}
                onMenu={() => onSongMenu?.(s)}
                accent={accent} density={density} showArt={false}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

Object.assign(window, { TopBar, SearchBar, SwipeableRow, LibraryScreen, PlaylistScreen, ArtistsScreen, ArtistScreen, AlbumRow, iconBtn });
