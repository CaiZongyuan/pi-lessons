#!/usr/bin/env python3
"""Losslessly encode deployed figures, retaining all original PNG sources.

Run after chapter importers and before VitePress. Pillow with WebP support is
required only when PNGs need encoding. Existing WebP files are retained and
verified against recorded source/output hashes without optional dependencies.
Regenerated PNGs are re-encoded. Only image fields in figure catalogs change.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'docs/public'
FIGURES = PUBLIC / 'figures'
REPORT = ROOT / 'sources/reports/webp-conversion.json'
SOURCE_ROOTS = [ROOT / 'sources/full', ROOT / 'sources/chapter']
CATALOGS = sorted((ROOT / 'docs/.vitepress/theme/figures').glob('book-*.json'))
CATALOGS.append(ROOT / 'docs/.vitepress/theme/components/figures.ts')
IMAGE_FIELD = re.compile(r'''((?:"image"|\bimage)\s*:\s*)(["'])([^"'\n]+)\2''')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def relative(path):
    return path.relative_to(ROOT).as_posix()


def rgba(path):
    from PIL import Image
    with Image.open(path) as image:
        if getattr(image, 'n_frames', 1) != 1:
            raise ValueError(f'Animated source is outside this conversion: {path}')
        decoded = image.convert('RGBA')
        return decoded.size, decoded.tobytes()


def main():
    pngs = sorted(FIGURES.rglob('*.png'))
    if pngs:
        try:
            from PIL import Image, features
        except ImportError:
            raise SystemExit('Encoding new PNGs requires Pillow: python3 -m pip install Pillow')
        if not features.check('webp'):
            raise SystemExit('Pillow requires WebP support; install Pillow with libwebp.')
    sources = sorted(p for base in SOURCE_ROOTS for p in base.rglob('*.png'))
    source_hashes = {relative(p): sha(p.read_bytes()) for p in sources}
    by_hash = {}
    for path, digest in source_hashes.items():
        by_hash.setdefault(digest, []).append(path)
    previous = json.loads(REPORT.read_text()) if REPORT.exists() else {'files': []}
    previous_by_output = {item['public_webp']: item for item in previous['files']}
    existing = sorted(p for p in FIGURES.rglob('*.webp') if not p.with_suffix('.png').exists())

    # A runnable delivery may omit optional immutable PNG audit packs. Verify
    # committed public hashes without pretending to repeat absent-source audits.
    expected_sources = {p: r['source_png_sha256'] for r in previous['files'] for p in r['sources']}
    missing_sources = set(expected_sources) - set(source_hashes)
    if missing_sources and not pngs:
        if any(digest != expected_sources.get(path) for path, digest in source_hashes.items()):
            raise ValueError('An included original source PNG changed')
        if {relative(p) for p in existing} != set(previous_by_output):
            raise ValueError('Project-only delivery has missing or unrecorded WebP assets')
        for output in existing:
            if sha(output.read_bytes()) != previous_by_output[relative(output)]['webp_sha256']:
                raise ValueError(f'Committed public asset changed: {relative(output)}')
        print(f"Verified {len(existing)} committed WebP hashes. Optional original PNG audit packs: "
              f"{len(source_hashes)}/{len(expected_sources)} included. Original pixel/source re-audit skipped: "
              "optional PNG packs are incomplete; restore both packs for full source audits.")
        return

    def convert_or_verify(public):
        is_png = public.suffix.lower() == '.png'
        output = public.with_suffix('.webp')
        if is_png:
            png_bytes = public.read_bytes()
            original_hash = sha(png_bytes)
            matching_sources = by_hash.get(original_hash, [])
            if not matching_sources:
                raise ValueError(f'No immutable original matches {relative(public)}')
            before_size = len(png_bytes)
            original = public
        else:
            old = previous_by_output.get(relative(output))
            if not old:
                raise ValueError(f'Existing WebP lacks source evidence: {relative(output)}')
            matching_sources = old['sources']
            original_hash = old['source_png_sha256']
            if not matching_sources or any(source_hashes.get(p) != original_hash for p in matching_sources):
                raise ValueError(f'Original source changed: {relative(output)}')
            original = ROOT / matching_sources[0]
            before_size = original.stat().st_size
            if not pngs:
                # The initial report binds exact-pixel evidence to both byte hashes.
                # Rechecking those hashes preserves that evidence without Pillow.
                if sha(output.read_bytes()) != old['webp_sha256']:
                    raise ValueError(f'Existing WebP changed: {relative(output)}')
                return dict(old)
        dimensions, pixels = rgba(original)
        if is_png:
            temporary = output.with_name(output.name + '.tmp')
            try:
                with Image.open(public) as source:
                    source.convert('RGBA').save(temporary, format='WEBP', lossless=True,
                                                quality=100, method=6, exact=True)
                actual_dimensions, actual_pixels = rgba(temporary)
                if dimensions != actual_dimensions or pixels != actual_pixels:
                    raise ValueError(f'Lossless verification failed: {relative(public)}')
                temporary.replace(output)
            finally:
                if temporary.exists():
                    temporary.unlink()
        else:
            actual_dimensions, actual_pixels = rgba(output)
            if dimensions != actual_dimensions or pixels != actual_pixels:
                raise ValueError(f'Existing WebP differs from original: {relative(output)}')
        return {
            'sources': matching_sources,
            'public_png_before': relative(public.with_suffix('.png')),
            'public_webp': relative(output),
            'width': dimensions[0], 'height': dimensions[1],
            'png_bytes': before_size, 'webp_bytes': output.stat().st_size,
            'source_png_sha256': original_hash,
            'decoded_rgba_sha256': sha(pixels),
            'webp_sha256': sha(output.read_bytes()),
            'dimensions_equal': True, 'decoded_rgba_pixels_equal': True,
        }

    # Independent encoders keep the import/build step fast, with bounded memory.
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(convert_or_verify, pngs + existing))
    records.sort(key=lambda entry: entry['public_webp'])

    def rewrite(match):
        prefix, quote, value = match.groups()
        if not value.lower().endswith(('.png', '.webp')):
            return match.group(0)
        target_value = value[:-4] + '.webp' if value.lower().endswith('.png') else value
        target = PUBLIC / unquote(target_value.lstrip('/')) if value.startswith('/') else FIGURES / unquote(target_value)
        if not target.is_file():
            raise ValueError(f'Catalog references a missing public asset: {target_value}')
        return prefix + quote + target_value + quote

    for catalog in CATALOGS:
        content = catalog.read_text()
        updated = IMAGE_FIELD.sub(rewrite, content)
        if updated != content:
            catalog.write_text(updated)
    if any(sha((ROOT / path).read_bytes()) != digest for path, digest in source_hashes.items()):
        raise ValueError('An immutable source file changed during conversion')
    before = sum(r['png_bytes'] for r in records)
    after = sum(r['webp_bytes'] for r in records)
    encoder = ({'library': 'Pillow', 'version': Image.__version__,
                'libwebp_version': features.version('webp'), 'format': 'WEBP',
                'lossless': True, 'quality': 100, 'method': 6, 'exact': True}
               if pngs else previous.get('encoder'))
    report = {
        'schema_version': 1,
        'scope': 'docs/public/figures/**/*.png; immutable sources retained as PNG',
        'encoder': encoder,
        'verification': 'Exact width, height, and every decoded RGBA byte compared with original PNG',
        'source_png_count': len(sources),
        'source_png_files_unchanged': True,
        'public_image_count': len(records),
        'before_png_bytes': before,
        'after_webp_bytes': after,
        'saved_bytes': before - after,
        'reduction_percent': round((1 - after / before) * 100, 4) if before else 0,
        'files': records,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temporary_report = REPORT.with_suffix('.json.tmp')
    temporary_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    temporary_report.replace(REPORT)
    # Keep the PNGs until all outputs, references, and recovery evidence are ready.
    # An interrupted run can safely resume using either PNGs or this report.
    for public in pngs:
        public.unlink()
    if list(FIGURES.rglob('*.png')):
        raise ValueError('Deployed PNG figures remain after conversion')
    print(f"Verified {len(records)} lossless WebP figures: {before:,} → {after:,} bytes "
          f"({report['reduction_percent']:.2f}% smaller). {len(sources)} source PNGs unchanged.")


if __name__ == '__main__':
    main()
