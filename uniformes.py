"""Gráficos locais de uniformes, reutilizados do painel de patrocínios."""
import calendar
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from datetime import date, datetime, timedelta
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont, ImageOps

from fm23 import ROOT
ASSETS = ROOT / 'assets'
DATA = ROOT / 'dados'
STATE = DATA / 'contratos.json'
GAME = Path.home() / 'Documents' / 'Sports Interactive' / 'Football Manager 2023'
DEST = GAME / 'graphics' / 'kits' / 'fm23_patrocinios_ceara'
CLUB_ID = 104749
KIT_VERSION = 2
KIT_FILES = ('home.png', 'away.png', 'third.png', 'home_3d.png', 'away_3d.png', 'third_3d.png', 'config.xml')
BASE_ANNUAL = 6414722  # Total observado no editor / dois anos de contrato.
OLD_END = date(2031, 12, 23)
BG, PANEL, FG, MUTED, ACCENT = '#10151d', '#1b2430', '#f0f3f7', '#9daebe', '#62dec1'


def money(n):
    return '£ ' + f'{int(n):,}'.replace(',', '.')


def amount(text):
    if not re.fullmatch(r'[\d., £]+', text.strip()):
        raise ValueError('Use um valor inteiro, por exemplo 7.500.000.')
    result = int(re.sub(r'\D', '', text))
    if not 1000 <= result <= 1_000_000_000:
        raise ValueError('Informe entre 1.000 e 1.000.000.000 libras por ano.')
    return result


def parse_date(text):
    try:
        return datetime.strptime(text, '%d/%m/%Y').date()
    except ValueError:
        raise ValueError('Informe uma data válida no formato dia/mês/ano.') from None


def end_date(start, years):
    # Uma vigência anual iniciada em 24/12 termina em 23/12 do ano seguinte.
    last_day = calendar.monthrange(start.year + years, start.month)[1]
    anniversary = start.replace(year=start.year + years, day=min(start.day, last_day))
    return anniversary if start.day > last_day else anniversary - timedelta(days=1)


def save_state(state, path=STATE):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, path)


def quote(company, years, start):
    seed = int(hashlib.sha256(f'{CLUB_ID}|{company["name"]}|{start}'.encode()).hexdigest()[:8], 16)
    market = BASE_ANNUAL * (0.94 + (seed % 23) / 100) * (1 + 0.035 * (years - 1))
    ceiling = round(market / 1000) * 1000
    return {'offer': round(ceiling * 0.86 / 1000) * 1000,
            'ceiling': ceiling, 'rounds': 0, 'closed': False}


def counteroffer(q, request):
    if q['closed']:
        raise ValueError('Essa negociação já foi encerrada.')
    q = dict(q)
    q['rounds'] += 1
    if request <= q['offer']:
        return q, 'A empresa mantém sua proposta atual; você pode aceitá-la.'
    if request <= q['ceiling']:
        q['offer'] = request
        return q, 'Contraproposta aceita pela empresa. Você pode assinar esse valor.'
    if q['rounds'] >= 3 or request > q['ceiling'] * 1.5:
        q['closed'] = True
        return q, 'A empresa encerrou a negociação para esta vigência.'
    q['offer'] = min(q['ceiling'], q['offer'] + round((q['ceiling'] - q['offer']) * 0.65 / 1000) * 1000)
    return q, 'A empresa recusou o pedido, mas melhorou a proposta.'


def font(size, bold=False):
    return ImageFont.truetype(str(Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' /
                                   ('seguisb.ttf' if bold else 'segoeui.ttf')), size)


def fit_logo(company, size):
    path = ASSETS / company['logo'] if company.get('logo') else None
    if path and path.is_file() and not company.get('art_type'):
        img = Image.open(path).convert('RGBA')
        if img.width * img.height > 20_000_000:
            raise ValueError('Logo muito grande.')
        box = img.getbbox()
        if box:
            img = img.crop(box)
        # O símbolo do Spotify é acompanhado do nome para leitura na camisa.
        if company['name'] == 'Spotify':
            wordmark = Image.new('RGBA', (650, 150))
            wordmark.alpha_composite(ImageOps.contain(img, (145, 145)), (0, 0))
            ImageDraw.Draw(wordmark).text((165, 5), 'Spotify', font=font(104, True), fill='#171717')
            img = wordmark
    else:
        img = Image.new('RGBA', (800, 180))
        draw = ImageDraw.Draw(img)
        f = font(100, True)
        draw.text((400, 90), company['name'][:32], font=f, anchor='mm', fill='#142230')
        img = img.crop(img.getbbox())
    return ImageOps.contain(img, size, Image.Resampling.LANCZOS)


def place(image, layer, center):
    image.alpha_composite(layer, (round(center[0] - layer.width / 2), round(center[1] - layer.height / 2)))


def active_sponsors(snapshot, contracts):
    """Vínculo gráfico: tolera normalização de início pelo FM, sem editar finanças.

    Fim, total e espaço precisam identificar uma única receita e uma única marca.
    O cadastro legado Samsung também pode ter sido movido para 'outro uniforme'.
    """
    today = snapshot['date']
    rows = [r for r in snapshot['sponsors'] if r['total'] and r['start'] <= today <= r['end']]
    eligible = [c for c in contracts if c.get('status') != 'terminated' and c['kind'] in {1, 8}
                and c['start'] <= today <= c['end']]
    bundle = {}
    for contract in eligible:
        def compatible(row):
            same_space = row['kind'] == contract['kind']
            legacy_shirt = not contract.get('transaction') and contract['kind'] == 1 and row['kind'] == 9
            return (same_space or legacy_shirt) and (row['end'], row['total']) == (contract['end'], contract['total'])
        candidates = [r for r in rows if compatible(r)]
        if len(candidates) != 1:
            continue
        row = candidates[0]
        identities = {c['company']['name'].casefold() for c in eligible
                      if (c['kind'], c['end'], c['total']) == (contract['kind'], row['end'], row['total'])}
        if len(identities) == 1:
            bundle[contract['kind']] = contract['company']
    return bundle


def kit_signature(bundle):
    payload = dict(version=KIT_VERSION, club=CLUB_ID, sponsors=bundle)
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def installation_ok(signature):
    try:
        manifest = json.loads((DEST / 'fmpresidente.json').read_text(encoding='utf-8'))
        return manifest['signature'] == signature and all(
            hashlib.sha256((DEST / name).read_bytes()).hexdigest() == manifest['files'][name]
            for name in KIT_FILES)
    except (OSError, ValueError, KeyError, TypeError):
        return False


def make_kit(company, kind='home', supplier=None):
    main = {'home': '#17191d', 'away': '#f1f2f3', 'third': '#252481'}[kind]
    trim = '#e9ebed' if kind != 'away' else '#20242a'
    img = Image.new('RGBA', (512, 512))
    d = ImageDraw.Draw(img)
    shape = [(164, 62), (217, 44), (295, 44), (348, 62), (448, 132),
             (400, 218), (350, 191), (358, 454), (154, 454), (162, 191), (112, 218), (64, 132)]
    d.polygon(shape, fill=main, outline='#4e535a', width=3)
    d.line([(70, 139), (115, 210)], fill=trim, width=14)
    d.line([(442, 139), (397, 210)], fill=trim, width=14)
    d.arc((212, 22, 300, 91), 0, 180, fill=trim, width=14)
    d.line([(162, 438), (350, 438)], fill=trim, width=3)
    # Costuras discretas; sem emblema de fabricante inventado.
    d.line([(166, 193), (159, 429)], fill='#747982', width=2)
    d.line([(346, 193), (353, 429)], fill='#747982', width=2)
    crest = ImageOps.contain(Image.open(ASSETS / 'ceara.png').convert('RGBA'), (57, 64))
    place(img, crest, (309, 148))
    if company:
        d.rounded_rectangle((169, 222, 343, 285), radius=8, fill='#fafafa')
        place(img, fit_logo(company, (155, 47)), (256, 253))
    if supplier:
        d.rounded_rectangle((174,130,244,166),radius=4,fill='#fafafa')
        place(img,fit_logo(supplier,(62,28)),(209,148))
    return img


def make_texture(company, kind, supplier=None):
    main = {'home': '#17191d', 'away': '#f1f2f3', 'third': '#252481'}[kind]
    trim = '#f1f2f3' if kind != 'away' else '#17191d'
    img = Image.new('RGBA', (1024, 1024), main)
    for part, color in [('shorts', trim), ('socks', main), ('collar', trim)]:
        mask = Image.open(ASSETS / f'{part}.png').convert('RGBA').getchannel('A')
        img.paste(color, (0, 0), mask)
    # UV padrão do FM anterior ao FM26: frente, escudo e master.
    crest = ImageOps.contain(Image.open(ASSETS / 'ceara.png').convert('RGBA'), (36, 43))
    place(img, crest, (207, 124))
    d = ImageDraw.Draw(img)
    if company:
        d.rounded_rectangle((56, 177, 248, 238), radius=5, fill='#fafafa')
        place(img, fit_logo(company, (176, 47)), (152, 207))
    if supplier:
        d.rounded_rectangle((72,111,137,137),radius=3,fill='#fafafa')
        place(img,fit_logo(supplier,(58,21)),(104,124))
    return img


def export_kits(company, folder, supplier=None):
    folder.mkdir(parents=True, exist_ok=True)
    root = ET.Element('record')
    ET.SubElement(root, 'boolean', id='preload', value='false')
    ET.SubElement(root, 'boolean', id='amap', value='false')
    maps = ET.SubElement(root, 'list', id='maps')
    for kind in ['home', 'away', 'third']:
        make_kit(company, kind, supplier).save(folder / f'{kind}.png')
        make_texture(company, kind, supplier).save(folder / f'{kind}_3d.png')
        ET.SubElement(maps, 'record', {'from': kind, 'to': f'graphics/pictures/team/{CLUB_ID}/kits/{kind}'})
        ET.SubElement(maps, 'record', {'from': f'{kind}_3d', 'to': f'graphics/pictures/team/{CLUB_ID}/kit_textures/{kind}'})
    ET.indent(root)
    ET.ElementTree(root).write(folder / 'config.xml', encoding='utf-8', xml_declaration=True)


def install_kits(folder, signature=None):
    expected = (GAME / 'graphics' / 'kits').resolve()
    if DEST.resolve().parent != expected or DEST.name != 'fm23_patrocinios_ceara':
        raise ValueError('Pasta de instalação inválida.')
    mappings = ET.parse(folder / 'config.xml').getroot().find("list[@id='maps']")
    required = {f'graphics/pictures/team/{CLUB_ID}/{group}/{kind}'
                for group in ('kits', 'kit_textures') for kind in ('home', 'away', 'third')}
    if mappings is None or {item.get('to') for item in mappings} != required:
        raise ValueError('O config.xml não aponta para os uniformes 2D e 3D do Ceará.')
    for name in KIT_FILES[:-1]:
        with Image.open(folder / name) as image:
            expected_size = (1024, 1024) if '_3d' in name else (512, 512)
            if image.size != expected_size:
                raise ValueError('Dimensões inválidas: ' + name)
            image.verify()
    if DEST.exists():
        backup = DATA / 'backups' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        shutil.copytree(DEST, backup)
    DEST.mkdir(parents=True, exist_ok=True)
    for name in KIT_FILES:
        temp = DEST / (name + '.tmp')
        shutil.copy2(folder / name, temp)
        os.replace(temp, DEST / name)
    manifest = dict(signature=signature, installed_at=datetime.now().isoformat(),
                    files={name: hashlib.sha256((DEST / name).read_bytes()).hexdigest() for name in KIT_FILES})
    save_state(manifest, DEST / 'fmpresidente.json')
    if signature and not installation_ok(signature):
        raise OSError('Falha na conferência dos uniformes instalados.')
