import argparse
import os
import re
from pathlib import Path
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

CLASS_DECL_RE = re.compile(r"^\s*\.class\b.*\b(L[^;]+;)")

DEFAULT_EXCLUDE_PREFIXES = (
    'Landroid/', 'Ljava/', 'Lkotlin/', 'Ljavax/', 'Lcom/android', 'Lcom/google'
)


def find_smali_classes(root_dir, exclude_prefixes):
    classes = set()
    files = []
    root = Path(root_dir)

    smali_dirs = []
    if root.is_dir():
        # include root itself if it looks like a smali dir
        if root.name.lower().startswith('smali'):
            smali_dirs.append(root)
        # find all nested directories starting with "smali"
        for d in root.rglob('*'):
            if d.is_dir() and d.name.lower().startswith('smali'):
                smali_dirs.append(d)

    # Collect .smali files from discovered smali directories or fallback to whole tree
    if smali_dirs:
        for sd in sorted(set(smali_dirs)):
            for p in sd.rglob('*.smali'):
                files.append(p)
    else:
        for p in root.rglob('*.smali'):
            files.append(p)

    # dedupe and sort for deterministic behavior
    files = sorted(set(files))

    for p in files:
        try:
            text = p.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        for line in text.splitlines():
            m = CLASS_DECL_RE.match(line)
            if m:
                cls = m.group(1)
                if not cls.startswith(exclude_prefixes):
                    classes.add(cls)
                break
    return classes, files


def gen_obf_name(index, prefix='La/obf/'):
    # produce like La/obf/A000;
    return 'L' + prefix.strip('L').rstrip('/') + f'/{index:05d};'


def build_mapping(classes, prefix='La/obf/'):
    mapping = {}
    i = 0
    for cls in sorted(classes):
        obf = gen_obf_name(i, prefix=prefix)
        mapping[cls] = obf
        i += 1
    return mapping


def replace_in_file(path, mapping):
    text = path.read_text(encoding='utf-8', errors='ignore')
    original_text = text
    # sort keys by length desc to avoid partial replacements
    for orig in sorted(mapping.keys(), key=len, reverse=True):
        obf = mapping[orig]
        text = text.replace(orig, obf)
    if text != original_text:
        path.write_text(text, encoding='utf-8')
        return True
    return False


def write_mapping(mapping, out_file):
    Path(out_file).parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, 'w', encoding='utf-8') as fh:
        for orig, obf in mapping.items():
            fh.write(f"{orig} -> {obf}\n")


def rename_files(files, mapping, root_dir):
    root = Path(root_dir)
    moved = 0
    for f in files:
        # try to find class declaration in file content
        text = f.read_text(encoding='utf-8', errors='ignore')
        m = CLASS_DECL_RE.search(text)
        orig = None
        if m:
            orig = m.group(1)
        else:
            # fallback: derive orig from file path by locating the nearest smali* dir
            parts = f.parts
            smali_idx = None
            for i in range(len(parts) - 1, -1, -1):
                if parts[i].lower().startswith('smali'):
                    smali_idx = i
                    break
            if smali_idx is not None:
                rel_parts = parts[smali_idx + 1 :]
            else:
                try:
                    rel_parts = f.relative_to(root).parts
                except Exception:
                    rel_parts = parts
            rel_path = Path(*rel_parts)
            class_name = str(rel_path).replace('\\', '/')
            if class_name.endswith('.smali'):
                class_name = class_name[:-6]
            orig = 'L' + class_name + ';'

        if orig not in mapping:
            continue

        obf = mapping[orig]
        # build destination path
        new_rel = obf[1:-1].replace('/', os.sep) + '.smali'  # strip leading L and trailing ;
        new_path = root.joinpath(new_rel)
        new_path.parent.mkdir(parents=True, exist_ok=True)
        # avoid overwrite; if exists, append suffix
        if new_path.exists():
            base = new_path.stem
            dirp = new_path.parent
            k = 1
            while True:
                candidate = dirp / (f"{base}__{k}.smali")
                if not candidate.exists():
                    new_path = candidate
                    break
                k += 1
        f.replace(new_path)
        moved += 1
    return moved


def parse_args():
    p = argparse.ArgumentParser(description='Smali class renamer / obfuscator')
    p.add_argument('--dir', '-d', default='.', help='root directory containing .smali files')
    p.add_argument('--prefix', default='La/obf', help='obfuscated package prefix (no leading L, e.g. La/obf)')
    p.add_argument('--out-mapping', default='mappings/class_mapping.txt', help='output mapping file')
    p.add_argument('--dry-run', action='store_true', help="don't write files, just show what would change")
    p.add_argument('--rename-files', action='store_true', help='move .smali files to match obfuscated class names')
    p.add_argument('--exclude', nargs='*', default=list(DEFAULT_EXCLUDE_PREFIXES), help='class prefixes to exclude')
    return p.parse_args()


def main():
    args = parse_args()
    root = args.dir
    exclude_prefixes = tuple(args.exclude)

    print(f"Scanning for classes in: {root}")
    classes, files = find_smali_classes(root, exclude_prefixes)
    print(f"Found {len(classes)} classes in {len(files)} files (excluded prefixes: {exclude_prefixes})")

    if not classes:
        print('No classes found to obfuscate. Exiting.')
        return

    mapping = build_mapping(classes, prefix=args.prefix)

    if args.dry_run:
        print('\nDry-run mapping (first 40 shown):')

    # replace references
    replaced_files = 0
    iterator = tqdm(files, desc="[Replacing references]") if tqdm else files
    for f in iterator:
        if replace_in_file(f, mapping):
            replaced_files += 1
    print(f"Updated {replaced_files} files with new class names.")

    # rename files if requested
    moved = 0
    if args.rename_files:
        iterator2 = tqdm(files, desc="[Renaming files]") if tqdm else files
        moved = rename_files(iterator2, mapping, root)
        print(f"Moved {moved} .smali files to match obfuscated class paths.")

    write_mapping(mapping, args.out_mapping)
    print(f"Wrote mapping to {args.out_mapping}")


if __name__ == '__main__':
    main()
