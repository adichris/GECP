import hashlib
import json
import pytest
from scripts.seed_all import main, validate_assets


def fixture_assets(folder):
    (folder / 'logo.png').write_bytes(b'example asset')
    entry = {'file': 'logo.png', 'sha256': hashlib.sha256(b'example asset').hexdigest()}
    (folder / 'manifest.json').write_text(json.dumps([entry]))
    (folder / 'illustration.png').write_bytes(b'illustration')
    (folder / 'illustration-provenance.json').write_text(json.dumps({'file': 'illustration.png', 'sha256': hashlib.sha256(b'illustration').hexdigest()}))


def test_all_assets_verified(tmp_path):
    fixture_assets(tmp_path)
    assert len(validate_assets(tmp_path)) == 2


def test_missing_and_modified_assets_fail(tmp_path):
    fixture_assets(tmp_path)
    (tmp_path / 'logo.png').write_bytes(b'changed')
    with pytest.raises(ValueError, match='checksum mismatch'):
        validate_assets(tmp_path)
    (tmp_path / 'logo.png').unlink()
    with pytest.raises(ValueError, match='Missing asset'):
        validate_assets(tmp_path)


def test_asset_path_cannot_escape_bundle(tmp_path):
    fixture_assets(tmp_path)
    (tmp_path / 'manifest.json').write_text(json.dumps([{'file': '../outside.png', 'sha256': 'invalid'}]))
    with pytest.raises(ValueError, match='Invalid or duplicate'):
        validate_assets(tmp_path)


def test_invalid_domain_fails_before_database_access():
    with pytest.raises(SystemExit) as error:
        main(['--domain', 'https://example.org', '--skip-assets'])
    assert error.value.code == 2


def test_asset_only_check_needs_no_database():
    assert main(['--check-assets']) == 0
