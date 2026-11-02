"""Regressão do vínculo após virada de temporada e da instalação real dos kits."""
from copy import deepcopy
from pathlib import Path
import tempfile
import uniformes as u
import fm23


def check():
    # O modo deve preservar todos os outros bits do mesmo byte do TEAM.
    class Flags:
        value=0xD5
        def number(self,address,fmt):
            assert address==4096+46 and fmt=='B'
            return self.value
    native=object.__new__(fm23.FM);native.mem=Flags();native.kit_team=lambda:4096
    changes=[]
    def transaction(title,items,meta):
        change=items[0];assert int(change['before'],16)==native.mem.value
        changes.append(change);native.mem.value=int(change['after'],16)
        return change
    native.transaction=transaction
    assert native.licensed_kits()
    native.set_licensed_kits(False);assert native.mem.value==0xDD and not native.licensed_kits()
    assert native.set_licensed_kits(False) is None
    native.set_licensed_kits(True);assert native.mem.value==0xD5 and native.licensed_kits()
    assert len(changes)==2
    visa = dict(company={'name': 'Visa'}, kind=8, start='2031-12-25', end='2033-12-24', total=10160000, transaction='signed')
    samsung = dict(company={'name': 'Samsung', 'logo': 'samsung.png'}, kind=1, start='2031-12-24', end='2033-12-23', total=7631000)
    rows = [dict(index=2, kind=8, start='2031-12-21', end=visa['end'], total=visa['total']),
            dict(index=3, kind=9, start='2031-12-21', end=samsung['end'], total=samsung['total'])]
    snapshot = dict(date='2031-12-25', sponsors=rows)
    original = deepcopy([visa, samsung, snapshot])
    bundle = u.active_sponsors(snapshot, [visa, samsung])
    assert {k: c['name'] for k, c in bundle.items()} == {1: 'Samsung', 8: 'Visa'}
    assert [visa, samsung, snapshot] == original
    assert 8 not in u.active_sponsors(dict(snapshot, date='2031-12-24'), [visa])
    assert not u.active_sponsors(dict(snapshot, date='2034-01-01'), [visa, samsung])
    assert not u.active_sponsors(dict(snapshot, sponsors=rows + [dict(rows[0], index=4)]), [visa])
    assert not u.active_sponsors(snapshot, [visa, dict(visa, company={'name': 'Outra marca'})])
    assert not u.active_sponsors(snapshot, [dict(visa, status='terminated')])
    assert not u.active_sponsors(dict(snapshot, sponsors=[dict(rows[0], total=1000)]), [visa])
    assert not u.active_sponsors(snapshot, [dict(samsung, transaction='other')])
    saved = u.GAME, u.DEST, u.DATA
    with tempfile.TemporaryDirectory() as folder:
        base = Path(folder)
        u.GAME = base / 'FM23'; u.DEST = u.GAME / 'graphics/kits/fm23_patrocinios_ceara'; u.DATA = base / 'app'
        try:
            source = base / 'render'
            u.export_kits(bundle[1], source, bundle[8])
            signature = u.kit_signature(bundle)
            u.install_kits(source, signature)
            assert u.installation_ok(signature)
            assert not u.installation_ok('outdated')
            (u.DEST / 'away_3d.png').write_bytes(b'broken')
            assert not u.installation_ok(signature)
            u.install_kits(source, signature)
            assert u.installation_ok(signature)
            (source / 'config.xml').write_text('<record><list id="maps"/></record>')
            try: u.install_kits(source, signature)
            except ValueError: pass
            else: raise AssertionError('Config inválido aceito')
            assert u.installation_ok(signature)
        finally: u.GAME, u.DEST, u.DATA = saved
    print('OK: modo nativo preserva flags; vínculo, ambiguidades, vigência e instalação 2D/3D com verificação e reparo.')


if __name__ == '__main__':
    check()
