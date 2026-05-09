// Spootify — Player, Search, Queue, Create Playlist

// ─── MINI PLAYER BAR ──────────────────────────────────────────────
function MiniPlayer({ song, artist, isPlaying, progress, liked, onToggle, onLike, onOpen, accent }) {
  if (!song) return null;
  return (
    <div onClick={onOpen} style={{
      margin: '0 8px 8px', borderRadius: 10, overflow: 'hidden', cursor: 'pointer',
      background: 'rgba(30,30,30,0.92)',
      backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)',
      boxShadow: '0 8px 28px rgba(0,0,0,0.4), inset 0 0 0 0.5px rgba(255,255,255,0.08)',
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px',
      }}>
        <Cover seed={song.album + song.artistId} coverUrl={song.coverUrl} size={40} radius={6} accent={accent} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            color: '#fff', fontSize: 13, fontWeight: 600, letterSpacing: -0.1,
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          }}>{song.title}</div>
          <div style={{
            color: 'rgba(255,255,255,0.6)', fontSize: 11, marginTop: 1,
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          }}>{artist?.name}</div>
        </div>
        <button onClick={(e) => { e.stopPropagation(); onLike(); }} style={{
          background: 'none', border: 'none', padding: 6, cursor: 'pointer',
        }}>
          {liked ? Icon.heartSm(18, accent) : Icon.heart(18, 'rgba(255,255,255,0.6)')}
        </button>
        <button onClick={(e) => { e.stopPropagation(); onToggle(); }} style={{
          width: 32, height: 32, borderRadius: '50%', border: 'none', cursor: 'pointer',
          background: accent, display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>{isPlaying ? Icon.pause(12, '#000') : Icon.play(12, '#000')}</button>
      </div>
      {/* progress line */}
      <div style={{ height: 2, background: 'rgba(255,255,255,0.08)' }}>
        <div style={{ height: '100%', width: `${progress * 100}%`, background: accent, transition: 'width 0.3s linear' }} />
      </div>
    </div>
  );
}

// ─── FULL PLAYER ──────────────────────────────────────────────────
function FullPlayer({ song, artist, isPlaying, progress, liked, shuffle, repeat,
  onToggle, onNext, onPrev, onLike, onClose, onShuffle, onRepeat, onSeek, onOpenQueue, onMenu, accent }) {
  if (!song) return null;
  const cur = song.dur * progress;

  return (
    <div style={{
      position: 'absolute', inset: 0, zIndex: 100,
      background: `linear-gradient(180deg, oklch(28% 0.04 ${hashHue(song.album+song.artistId)}) 0%, #0a0a0a 60%)`,
      display: 'flex', flexDirection: 'column',
      paddingTop: 54,
    }}>
      {/* Top bar */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '8px 16px',
      }}>
        <button onClick={onClose} style={{ ...iconBtn, background: 'transparent' }}>{Icon.chevDown(20)}</button>
        <div style={{ textAlign: 'center' }}>
          <div style={{ color: 'rgba(255,255,255,0.55)', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1.5 }}>Reproduciendo</div>
          <div style={{ color: '#fff', fontSize: 13, fontWeight: 600 }}>{song.album}</div>
        </div>
        <button onClick={onMenu} style={{ ...iconBtn, background: 'transparent' }}>{Icon.dots(18)}</button>
      </div>

      {/* Cover */}
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '12px 28px' }}>
        <Cover seed={song.album + song.artistId} coverUrl={song.coverUrl} size={320} radius={14} accent={accent} />
      </div>

      {/* Meta */}
      <div style={{ padding: '0 28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{
              color: '#fff', fontSize: 22, fontWeight: 700, letterSpacing: -0.4,
              fontFamily: '"Space Grotesk", -apple-system, system-ui',
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            }}>{song.title}</div>
            <div style={{
              color: 'rgba(255,255,255,0.65)', fontSize: 14, marginTop: 2,
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            }}>{artist?.name}</div>
          </div>
          <button onClick={onLike} style={{ background: 'none', border: 'none', padding: 6, cursor: 'pointer' }}>
            {liked ? Icon.heart(26, accent, true) : Icon.heart(26, 'rgba(255,255,255,0.7)')}
          </button>
        </div>

        {/* Scrubber */}
        <div style={{ marginTop: 18 }}>
          <div onClick={(e) => {
            const r = e.currentTarget.getBoundingClientRect();
            onSeek((e.clientX - r.left) / r.width);
          }} style={{
            height: 12, display: 'flex', alignItems: 'center', cursor: 'pointer',
          }}>
            <div style={{ height: 3, width: '100%', background: 'rgba(255,255,255,0.15)', borderRadius: 99, position: 'relative' }}>
              <div style={{ height: '100%', width: `${progress*100}%`, background: '#fff', borderRadius: 99 }} />
              <div style={{
                position: 'absolute', top: '50%', left: `${progress*100}%`,
                transform: 'translate(-50%, -50%)',
                width: 10, height: 10, borderRadius: '50%', background: '#fff',
              }} />
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4, fontVariantNumeric: 'tabular-nums' }}>
            <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: 11 }}>{fmtDur(Math.floor(cur))}</span>
            <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: 11 }}>-{fmtDur(Math.max(0, song.dur - Math.floor(cur)))}</span>
          </div>
        </div>

        {/* Controls */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '18px 0',
        }}>
          <button onClick={onShuffle} style={ctrlBtn}>
            {Icon.shuffle(18, shuffle ? accent : 'rgba(255,255,255,0.7)')}
            {shuffle && <div style={{ position: 'absolute', bottom: 2, width: 3, height: 3, borderRadius: '50%', background: accent }} />}
          </button>
          <button onClick={onPrev} style={ctrlBtn}>{Icon.prev(28, '#fff')}</button>
          <button onClick={onToggle} style={{
            width: 64, height: 64, borderRadius: '50%', border: 'none', cursor: 'pointer',
            background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>{isPlaying ? Icon.pause(22, '#000') : Icon.play(22, '#000')}</button>
          <button onClick={onNext} style={ctrlBtn}>{Icon.next(28, '#fff')}</button>
          <button onClick={onRepeat} style={ctrlBtn}>
            {Icon.repeat(18, repeat !== 'off' ? accent : 'rgba(255,255,255,0.7)')}
            {repeat === 'one' && <div style={{ position: 'absolute', top: -1, right: 10, fontSize: 7, color: accent, fontWeight: 700 }}>1</div>}
            {repeat !== 'off' && <div style={{ position: 'absolute', bottom: 2, width: 3, height: 3, borderRadius: '50%', background: accent }} />}
          </button>
        </div>

        {/* Bottom row */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          paddingBottom: 22,
        }}>
          <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: 11, display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: accent }} />
            Salón · Reproduciendo en esta sesión
          </div>
          <button onClick={onOpenQueue} style={{ background: 'none', border: 'none', padding: 6, cursor: 'pointer' }}>
            {Icon.queue(18, 'rgba(255,255,255,0.8)')}
          </button>
        </div>
      </div>
    </div>
  );
}

const ctrlBtn = {
  background: 'none', border: 'none', cursor: 'pointer', padding: 8,
  position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center',
};

// ─── QUEUE ────────────────────────────────────────────────────────
function QueueScreen({ queue, songs, artists, currentIndex, onClose, onJump, onSongMenu, accent }) {
  const artistsById = useMemo(() => Object.fromEntries(artists.map(a => [a.id, a])), [artists]);
  const songsById = useMemo(() => Object.fromEntries(songs.map(s => [s.id, s])), [songs]);

  const now = queue[currentIndex] ? songsById[queue[currentIndex]] : null;
  const next = queue.slice(currentIndex + 1).map(id => songsById[id]).filter(Boolean);

  return (
    <div style={{ position: 'absolute', inset: 0, zIndex: 200, background: '#0a0a0a', display: 'flex', flexDirection: 'column', paddingTop: 54 }}>
      <TopBar onBack={onClose} title="Cola" accent={accent} />
      <div style={{ flex: 1, overflowY: 'auto', paddingBottom: 40 }}>
        {now && (
          <>
            <div style={{ padding: '12px 16px 6px', color: 'rgba(255,255,255,0.5)', fontSize: 11, textTransform: 'uppercase', letterSpacing: 1.5, fontWeight: 600 }}>Reproduciendo</div>
            <SongRow song={now} artist={artistsById[now.artistId]} index={currentIndex}
              isCurrent isPlaying liked={false} onPlay={() => {}} onMenu={() => onSongMenu?.(now)} accent={accent} showArt={true} />
          </>
        )}
        {next.length > 0 && (
          <>
            <div style={{ padding: '16px 16px 6px', color: 'rgba(255,255,255,0.5)', fontSize: 11, textTransform: 'uppercase', letterSpacing: 1.5, fontWeight: 600 }}>A continuación</div>
            {next.map((s, i) => (
              <SongRow key={`${s.id}-${i}`} song={s} artist={artistsById[s.artistId]} index={i}
                onPlay={() => onJump(currentIndex + 1 + i)}
                onMenu={() => onSongMenu?.(s)}
                accent={accent} showArt={true} />
            ))}
          </>
        )}
      </div>
    </div>
  );
}

// ─── SEARCH ───────────────────────────────────────────────────────
function SearchScreen({ songs, artists, playlists, likedIds, onPlaySong, onLike, onOpenArtist, onOpenPlaylist, onSongMenu, accent }) {
  const [q, setQ] = useState('');
  const artistsById = useMemo(() => Object.fromEntries(artists.map(a => [a.id, a])), [artists]);

  const matches = useMemo(() => {
    const qq = q.trim().toLowerCase();
    if (!qq) return { songs: [], artists: [], playlists: [] };
    return {
      songs: songs.filter(s => s.title.toLowerCase().includes(qq) || s.album.toLowerCase().includes(qq) || artistsById[s.artistId].name.toLowerCase().includes(qq)).slice(0, 20),
      artists: artists.filter(a => a.name.toLowerCase().includes(qq)),
      playlists: playlists.filter(p => p.title.toLowerCase().includes(qq)),
    };
  }, [q, songs, artists, playlists]);

  return (
    <div style={{ paddingBottom: 140 }}>
      <div style={{ padding: '14px 16px 4px' }}>
        <h1 style={{
          margin: 0, color: '#fff', fontSize: 24, fontWeight: 700, letterSpacing: -0.5,
          fontFamily: '"Space Grotesk", -apple-system, system-ui',
        }}>Buscar</h1>
      </div>
      <div style={{ padding: '10px 16px' }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8, padding: '10px 12px',
          borderRadius: 10, background: 'rgba(255,255,255,0.08)',
        }}>
          {Icon.search(16, 'rgba(255,255,255,0.5)')}
          <input autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder="Artista, canción o playlist" style={{
            flex: 1, background: 'transparent', border: 'none', outline: 'none',
            color: '#fff', fontSize: 14, fontFamily: 'inherit',
          }} />
          {q && <button onClick={() => setQ('')} style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.5)', fontSize: 12, cursor: 'pointer' }}>Cancelar</button>}
        </div>
      </div>

      {!q.trim() && (
        <div style={{ padding: '18px 16px' }}>
          <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: 11, textTransform: 'uppercase', letterSpacing: 1.5, fontWeight: 600, marginBottom: 10 }}>Explora por género</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            {['Indie Rock', 'Post-Rock', 'Garage', 'Punk', 'Stoner', 'Alt Rock'].map(g => (
              <div key={g} style={{
                height: 84, borderRadius: 10, padding: 12,
                background: coverGradient(g, accent),
                color: 'rgba(255,255,255,0.85)', fontWeight: 700, fontSize: 16,
                fontFamily: '"Space Grotesk", -apple-system, system-ui',
                letterSpacing: -0.3,
              }}>{g}</div>
            ))}
          </div>
        </div>
      )}

      {q.trim() && (
        <div>
          {matches.artists.length > 0 && (
            <>
              <SectionHeader title="Artistas" />
              {matches.artists.map(a => (
                <div key={a.id} onClick={() => onOpenArtist(a.id)} style={rowStyle}>
                  <ArtistAvatar seed={a.name} size={48} initials={a.name.split(' ').map(w => w[0]).slice(0,2).join('')} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ color: '#fff', fontSize: 15, fontWeight: 600 }}>{a.name}</div>
                    <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13 }}>Artista · {a.genre}</div>
                  </div>
                </div>
              ))}
            </>
          )}
          {matches.playlists.length > 0 && (
            <>
              <SectionHeader title="Playlists" />
              {matches.playlists.map(p => (
                <div key={p.id} onClick={() => onOpenPlaylist(p.id)} style={rowStyle}>
                  <Cover seed={p.title} size={48} radius={6} accent={accent} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ color: '#fff', fontSize: 15, fontWeight: 600 }}>{p.title}</div>
                    <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13 }}>Playlist · {p.items.length}</div>
                  </div>
                </div>
              ))}
            </>
          )}
          {matches.songs.length > 0 && (
            <>
              <SectionHeader title="Canciones" />
              {matches.songs.map((s, i) => (
                <SongRow key={s.id} song={s} artist={artistsById[s.artistId]} index={i}
                  liked={likedIds.includes(s.id)}
                  onPlay={() => onPlaySong(s.id, matches.songs.map(x => x.id))}
                  onLike={() => onLike(s.id)}
                  accent={accent} showArt={true} />
              ))}
            </>
          )}
          {matches.songs.length === 0 && matches.artists.length === 0 && matches.playlists.length === 0 && (
            <div style={{ padding: 40, textAlign: 'center', color: 'rgba(255,255,255,0.4)', fontSize: 14 }}>
              Sin resultados para "{q}"
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const rowStyle = { display: 'flex', alignItems: 'center', gap: 12, padding: '8px 16px', cursor: 'pointer' };
function SectionHeader({ title }) {
  return <div style={{ padding: '14px 16px 6px', color: 'rgba(255,255,255,0.5)', fontSize: 11, textTransform: 'uppercase', letterSpacing: 1.5, fontWeight: 600 }}>{title}</div>;
}

// ─── CREATE PLAYLIST SHEET ────────────────────────────────────────
function CreatePlaylistSheet({ onClose, onCreate, accent }) {
  const [name, setName] = useState('Mi playlist #' + Math.floor(Math.random() * 100));
  return (
    <BottomSheet onClose={onClose} zIndex={300}>
      {(close) => (
        <div style={{ padding: '10px 20px 32px' }}>
          <div style={{ color: '#fff', fontSize: 18, fontWeight: 700, letterSpacing: -0.3, marginBottom: 14, fontFamily: '"Space Grotesk", -apple-system, system-ui' }}>Nueva playlist</div>
          <input autoFocus value={name} onChange={(e) => setName(e.target.value)} style={{
            width: '100%', boxSizing: 'border-box', background: 'rgba(255,255,255,0.08)',
            border: 'none', outline: 'none', padding: '12px 14px', borderRadius: 10,
            color: '#fff', fontSize: 15, fontFamily: 'inherit',
          }} />
          <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
            <button onClick={close} style={{
              flex: 1, padding: '12px', borderRadius: 10, border: 'none', cursor: 'pointer',
              background: 'rgba(255,255,255,0.08)', color: '#fff', fontSize: 14, fontWeight: 600,
            }}>Cancelar</button>
            <button onClick={() => { onCreate(name.trim() || 'Nueva playlist'); }} style={{
              flex: 1, padding: '12px', borderRadius: 10, border: 'none', cursor: 'pointer',
              background: accent, color: '#000', fontSize: 14, fontWeight: 700,
            }}>Crear</button>
          </div>
        </div>
      )}
    </BottomSheet>
  );
}

Object.assign(window, { MiniPlayer, FullPlayer, QueueScreen, SearchScreen, CreatePlaylistSheet, SongMenuSheet, PlaylistPickerSheet, EditPlaylistSheet });

// ─── SONG CONTEXT MENU ────────────────────────────────────────────
function SongMenuSheet({ song, artist, liked, onClose, onGoArtist, onGoAlbum, onAddQueue, onAddPlaylist, onToggleLike, accent }) {
  return (
    <BottomSheet onClose={onClose} zIndex={310}>
      {(close) => {
        const wrap = (fn) => () => { fn?.(); close(); };
        const item = (icon, label, onClick, color = '#fff') => (
          <button onClick={onClick} style={{
            display: 'flex', alignItems: 'center', gap: 14, width: '100%',
            padding: '14px 6px', background: 'none', border: 'none', cursor: 'pointer',
            color, fontSize: 15, textAlign: 'left', fontFamily: 'inherit',
            borderBottom: '0.5px solid rgba(255,255,255,0.06)',
          }}>
            <div style={{ width: 22, display: 'flex', justifyContent: 'center' }}>{icon}</div>
            {label}
          </button>
        );
        return (
          <div style={{ padding: '8px 20px 28px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
              <Cover seed={song.album + song.artistId} size={44} radius={6} accent={accent} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ color: '#fff', fontSize: 15, fontWeight: 600, letterSpacing: -0.2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{song.title}</div>
                <div style={{ color: 'rgba(255,255,255,0.55)', fontSize: 12, marginTop: 2 }}>{artist?.name} · {song.album}</div>
              </div>
            </div>
            {item(liked ? Icon.heartSm(18, accent) : Icon.heart(18, 'rgba(255,255,255,0.8)'), liked ? 'Quitar de Canciones guardadas' : 'Guardar en Canciones guardadas', wrap(onToggleLike))}
            {item(Icon.queue(18, 'rgba(255,255,255,0.8)'), 'Añadir a la cola', wrap(onAddQueue))}
            {item(Icon.plus(18, 'rgba(255,255,255,0.8)'), 'Añadir a playlist…', wrap(onAddPlaylist))}
            {item(Icon.mic(18, 'rgba(255,255,255,0.8)'), `Ir a ${artist?.name}`, wrap(onGoArtist))}
            {item(Icon.library(18, 'rgba(255,255,255,0.8)'), `Ir al álbum`, wrap(onGoAlbum), '#fff')}
          </div>
        );
      }}
    </BottomSheet>
  );
}

// ─── PLAYLIST PICKER ──────────────────────────────────────────────
function PlaylistPickerSheet({ songId, playlists, onClose, onPick, onCreate, accent }) {
  return (
    <BottomSheet onClose={onClose} zIndex={320}>
      {(close) => (
        <>
          <div style={{ padding: '0 20px', color: '#fff', fontSize: 17, fontWeight: 700, letterSpacing: -0.3, marginBottom: 8 }}>Añadir a playlist</div>
          <button onClick={() => { onCreate(); }} style={{
            display: 'flex', alignItems: 'center', gap: 14, padding: '12px 20px',
            background: 'none', border: 'none', cursor: 'pointer', color: accent,
            fontSize: 14, fontWeight: 600, fontFamily: 'inherit', textAlign: 'left',
          }}>
            <div style={{
              width: 44, height: 44, borderRadius: 8, background: 'rgba(255,255,255,0.06)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>{Icon.plus(20, accent)}</div>
            Nueva playlist
          </button>
          <div style={{ overflowY: 'auto', paddingBottom: 24 }}>
            {playlists.map(p => {
              const has = p.items.find(it => it.id === songId);
              return (
                <button key={p.id} onClick={() => { onPick(p.id); close(); }} style={{
                  display: 'flex', alignItems: 'center', gap: 14, padding: '8px 20px',
                  background: 'none', border: 'none', cursor: 'pointer', width: '100%',
                  color: '#fff', fontSize: 14, textAlign: 'left', fontFamily: 'inherit',
                }}>
                  {p.id === 'saved' ? (
                    <div style={{
                      width: 44, height: 44, borderRadius: 8,
                      background: `linear-gradient(135deg, ${accent} 0%, oklch(55% 0.14 145) 100%)`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>{Icon.heart(20, '#000', true)}</div>
                  ) : (
                    <Cover seed={p.title} size={44} radius={6} accent={accent} />
                  )}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, letterSpacing: -0.2 }}>{p.title}</div>
                    <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: 12, marginTop: 2 }}>
                      {p.items.length} canciones{has ? ' · Ya incluida' : ''}
                    </div>
                  </div>
                  {has && <span style={{ color: accent, fontSize: 16 }}>✓</span>}
                </button>
              );
            })}
          </div>
        </>
      )}
    </BottomSheet>
  );
}


// ─── EDIT PLAYLIST ────────────────────────────────────────────────
function EditPlaylistSheet({ playlist, songs, artists, onClose, onSave, accent }) {
  const isSaved = playlist.id === 'saved';
  const [title, setTitle] = useState(playlist.title);
  const [coverSeed, setCoverSeed] = useState(playlist.coverSeed || playlist.title);
  const [order, setOrder] = useState(playlist.items.map(it => it.id));
  const [dragId, setDragId] = useState(null);
  const [overId, setOverId] = useState(null);
  const artistsById = useMemo(() => Object.fromEntries(artists.map(a => [a.id, a])), [artists]);
  const songsById = useMemo(() => Object.fromEntries(songs.map(s => [s.id, s])), [songs]);

  // Cover palette options: title-based + alternate seeds
  const coverOptions = useMemo(() => {
    const base = [playlist.title, playlist.title + '·alt', playlist.title + '·2', playlist.title + '·3', playlist.title + '·4', playlist.title + '·5'];
    // also include first few song+album as option
    const extras = playlist.items.slice(0, 4).map(it => {
      const s = songsById[it.id];
      return s ? s.album + s.artistId : null;
    }).filter(Boolean);
    return [...base, ...extras];
  }, [playlist, songsById]);

  const onDragStart = (id) => (e) => {
    setDragId(id);
    e.dataTransfer.effectAllowed = 'move';
  };
  const onDragOver = (id) => (e) => {
    e.preventDefault();
    setOverId(id);
  };
  const onDrop = (id) => (e) => {
    e.preventDefault();
    if (!dragId || dragId === id) { setDragId(null); setOverId(null); return; }
    const next = [...order];
    const from = next.indexOf(dragId);
    const to = next.indexOf(id);
    next.splice(from, 1);
    next.splice(to, 0, dragId);
    setOrder(next);
    setDragId(null);
    setOverId(null);
  };

  return (
    <BottomSheet onClose={onClose} zIndex={315} maxHeight="92%">
      {(close) => (
        <>
          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 16px 12px', flexShrink: 0 }}>
            <button onClick={close} style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.7)', fontSize: 14, cursor: 'pointer', fontFamily: 'inherit', padding: 6 }}>Cancelar</button>
            <div style={{ color: '#fff', fontSize: 15, fontWeight: 700, letterSpacing: -0.2 }}>{isSaved ? 'Editar orden' : 'Editar playlist'}</div>
            <button onClick={() => { onSave({ title: title.trim() || playlist.title, coverSeed, order }); close(); }} style={{
              background: 'none', border: 'none', color: accent, fontSize: 14, fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit', padding: 6,
            }}>Guardar</button>
          </div>

          <div style={{ overflowY: 'auto', padding: '0 16px 28px' }}>
            {!isSaved && (<>
            {/* Cover + title */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '8px 0 14px' }}>
              <Cover seed={coverSeed} size={128} radius={10} accent={accent} label={(title || '').slice(0,10)} />
              <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: 11, marginTop: 10, textTransform: 'uppercase', letterSpacing: 1.2, fontWeight: 600 }}>Miniatura</div>
              <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap', justifyContent: 'center' }}>
                {coverOptions.map((s, i) => (
                  <button key={i} onClick={() => setCoverSeed(s)} style={{
                    padding: 0, border: coverSeed === s ? `2px solid ${accent}` : '2px solid transparent', background: 'none', cursor: 'pointer', borderRadius: 8,
                  }}>
                    <Cover seed={s} size={44} radius={6} accent={accent} />
                  </button>
                ))}
              </div>
            </div>

            {/* Title input */}
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Nombre" style={{
              width: '100%', boxSizing: 'border-box', background: 'rgba(255,255,255,0.08)',
              border: 'none', outline: 'none', padding: '12px 14px', borderRadius: 10,
              color: '#fff', fontSize: 15, fontFamily: 'inherit', marginBottom: 14,
            }} />
            </>)}

            {/* Reorder */}
            <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: 11, textTransform: 'uppercase', letterSpacing: 1.2, fontWeight: 600, padding: '6px 2px 6px' }}>
              Orden personalizado · arrastra
            </div>
            <div>
              {order.map(id => {
                const s = songsById[id]; if (!s) return null;
                const a = artistsById[s.artistId];
                const isDragging = dragId === id;
                const isOver = overId === id && dragId && dragId !== id;
                return (
                  <div key={id}
                    draggable
                    onDragStart={onDragStart(id)}
                    onDragOver={onDragOver(id)}
                    onDragEnd={() => { setDragId(null); setOverId(null); }}
                    onDrop={onDrop(id)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 12, padding: '10px 4px',
                      borderTop: isOver ? `2px solid ${accent}` : '2px solid transparent',
                      opacity: isDragging ? 0.4 : 1,
                      cursor: 'grab',
                    }}>
                    <div style={{ width: 20, color: 'rgba(255,255,255,0.4)', display: 'flex', flexDirection: 'column', gap: 2 }}>
                      <div style={{ height: 1.5, background: 'currentColor', borderRadius: 1 }} />
                      <div style={{ height: 1.5, background: 'currentColor', borderRadius: 1 }} />
                      <div style={{ height: 1.5, background: 'currentColor', borderRadius: 1 }} />
                    </div>
                    <Cover seed={s.album + s.artistId} size={40} radius={5} accent={accent} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ color: '#fff', fontSize: 14, fontWeight: 500, letterSpacing: -0.1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.title}</div>
                      <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: 12, marginTop: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{a?.name}</div>
                    </div>
                    <button onClick={() => setOrder(order.filter(x => x !== id))} style={{
                      background: 'none', border: 'none', color: 'rgba(255,255,255,0.4)', cursor: 'pointer',
                      fontSize: 20, padding: '2px 8px', lineHeight: 1,
                    }}>−</button>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </BottomSheet>
  );
}
