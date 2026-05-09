from __future__ import annotations

from pathlib import Path

from mutagen.id3 import APIC, ID3, TALB, TIT2, TPE1

from spootify.artwork import album_dir_for, save_album_cover


# Un JPEG mínimo válido (2x2 blanco). Suficiente para tests.
_JPEG_BYTES = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000"
    "ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432"
    "ffdb0043010909090c0b0c180d0d1832211c2132323232323232323232323232323232323232323232323232323232323232323232323232323232323232323232323232"
    "ffc000110800020002030122000211010311"
    "01ffc4001f0000010501010101010100000000000000000102030405060708090a0b"
    "ffc400b5100002010303020403050504040000017d01020300041105122131410613516107227114328191a1082342b1c11552d1f02433627282090a161718191a25262728292a3435363738393a434445464748494a535455565758595a636465666768696a737475767778797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9fa"
    "ffc4001f0100030101010101010101010000000000000102030405060708090a0b"
    "ffc400b51100020102040403040705040400010277000102031104052131061241510761711322328108144291a1b1c109233352f0156272d10a162434e125f11718191a262728292a35363738393a434445464748494a535455565758595a636465666768696a737475767778797a82838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae2e3e4e5e6e7e8e9eaf2f3f4f5f6f7f8f9fa"
    "ffda000c03010002110311003f00fbd4b2f3ffd9"
)


def _make_mp3_with_tags(path: Path, jpeg_bytes: bytes = _JPEG_BYTES) -> None:
    # Escribe un MP3 mínimo con tags ID3. Para los tests no necesitamos audio
    # válido — mutagen solo lee las cabeceras ID3 al inicio.
    path.write_bytes(b"\x00" * 4096)
    tags = ID3()
    tags.add(TIT2(encoding=3, text="Test Track"))
    tags.add(TPE1(encoding=3, text="Test Artist"))
    tags.add(TALB(encoding=3, text="Test Album"))
    tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=jpeg_bytes))
    tags.save(path)


def test_album_dir_with_disc_folder(tmp_path: Path) -> None:
    track = tmp_path / "Artist" / "Album" / "Disc 1" / "01. x.mp3"
    track.parent.mkdir(parents=True)
    track.write_bytes(b"")
    assert album_dir_for(track) == tmp_path / "Artist" / "Album"


def test_album_dir_without_disc_folder(tmp_path: Path) -> None:
    track = tmp_path / "Artist" / "Album" / "01. x.mp3"
    track.parent.mkdir(parents=True)
    track.write_bytes(b"")
    assert album_dir_for(track) == tmp_path / "Artist" / "Album"


def test_save_cover_creates_jpg(tmp_path: Path) -> None:
    disc = tmp_path / "Artist" / "Album" / "Disc 1"
    disc.mkdir(parents=True)
    mp3 = disc / "01. track.mp3"
    _make_mp3_with_tags(mp3)

    result = save_album_cover(mp3)
    expected = tmp_path / "Artist" / "Album" / "cover.jpg"
    assert result == expected
    assert expected.exists()
    assert expected.read_bytes() == _JPEG_BYTES


def test_save_cover_skips_if_exists(tmp_path: Path) -> None:
    album = tmp_path / "Artist" / "Album"
    (album / "Disc 1").mkdir(parents=True)
    mp3 = album / "Disc 1" / "01. track.mp3"
    _make_mp3_with_tags(mp3)
    existing = album / "cover.jpg"
    existing.write_bytes(b"already here")

    result = save_album_cover(mp3)
    assert result is None
    assert existing.read_bytes() == b"already here"


def test_save_cover_overwrites_when_flag(tmp_path: Path) -> None:
    album = tmp_path / "Artist" / "Album"
    album.mkdir(parents=True)
    mp3 = album / "01. track.mp3"
    _make_mp3_with_tags(mp3)
    (album / "cover.jpg").write_bytes(b"old")

    save_album_cover(mp3, overwrite=True)
    assert (album / "cover.jpg").read_bytes() == _JPEG_BYTES


def test_save_cover_no_apic_returns_none(tmp_path: Path) -> None:
    album = tmp_path / "Artist" / "Album"
    album.mkdir(parents=True)
    mp3 = album / "01. track.mp3"
    mp3.write_bytes(b"\x00" * 4096)
    tags = ID3()
    tags.add(TIT2(encoding=3, text="Test"))
    tags.save(mp3)

    assert save_album_cover(mp3) is None
    assert not (album / "cover.jpg").exists()
