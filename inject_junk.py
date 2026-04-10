from pathlib import Path
import argparse
import shutil
import os
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


def find_smali_dir(root: Path) -> Path:
    if not root.exists():
        raise FileNotFoundError(root)
    if root.name.lower().startswith('smali'):
        return root
    for d in root.rglob('*'):
        if d.is_dir() and d.name.lower().startswith('smali'):
            return d
    return root


def build_helper(prefix: str, class_name: str, count: int) -> str:
    pkg = prefix.lstrip('L').rstrip('/')
    lines = [f".class public L{pkg}/{class_name};", ".super Ljava/lang/Object;", ""]
    lines += [".method public constructor <init>()V", "    .locals 0", "    invoke-direct {p0}, Ljava/lang/Object;-><init>()V", "    return-void", ".end method", ""]
    for i in range(count):
        a = (i * 17 + 3) & 0xFF
        b = (i * 11 + 5) & 0xFF
        lines += [
            f".method public static opaqueV{i}()V",
            "    .locals 2",
            f"    const/16 v0, 0x{a:x}",
            f"    const/16 v1, 0x{b:x}",
            "    add-int v0, v0, v1",
            "    and-int/lit8 v0, v0, -1",
            "    return-void",
            ".end method",
            "",
        ]
    return "\n".join(lines)


def write_helper(smali_dir: Path, prefix: str, class_name: str, text: str, dry_run: bool, force: bool):
    pkg_rel = prefix.lstrip('L').rstrip('/').replace('/', os.sep)
    dest = smali_dir.joinpath(pkg_rel)
    dest_file = dest.joinpath(f"{class_name}.smali")
    print(f"Helper target: {dest_file}")
    if dry_run:
        print('\n'.join(text.splitlines()[:40]))
        return dest_file
    dest.mkdir(parents=True, exist_ok=True)
    if dest_file.exists() and not force:
        print(f"Helper exists: {dest_file} (use --force to overwrite)")
        return dest_file
    dest_file.write_text(text, encoding='utf-8')
    print(f"Wrote helper: {dest_file}")
    return dest_file


def inject(smali_root: Path, helper_prefix: str, helper_class: str, count: int, mode: str, target_prefix: str, max_per_file: int, dry_run: bool):
    pkg = helper_prefix.lstrip('L').rstrip('/')
    helper_ref = f"L{pkg}/{helper_class};"
    smali_files = list(smali_root.rglob('*.smali'))
    total = 0
    iterator = tqdm(smali_files, desc="[Injecting junk]") if tqdm else smali_files
    for sf in iterator:
        sfn = str(sf).replace('\\', '/')
        if helper_ref in sfn or sf.name == f"{helper_class}.smali":
            continue
        if target_prefix:
            tp = target_prefix.replace('.', '/').strip('/')
            if tp not in sfn:
                continue
        text = sf.read_text(encoding='utf-8', errors='ignore')
        lines = text.splitlines()
        out = []
        i = 0
        per = 0
        changed = False
        while i < len(lines):
            line = lines[i]
            if line.strip().startswith('.method'):
                block = [line]
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('.end method'):
                    block.append(lines[i])
                    i += 1
                if i < len(lines):
                    block.append(lines[i])
                hdr = block[0]
                if '<init>' in hdr or 'abstract' in hdr or 'native' in hdr:
                    out.extend(block)
                else:
                    if per < max_per_file:
                        if mode == 'before_return':
                            inserted = False
                            newb = []
                            for ml in block:
                                if not inserted and ml.strip().startswith('return'):
                                    idx = total % count
                                    newb.append(f"    invoke-static {{}}, {helper_ref}->opaqueV{idx}()V")
                                    inserted = True
                                    per += 1
                                    total += 1
                                    changed = True
                                newb.append(ml)
                            out.extend(newb)
                        else:
                            newb = []
                            inserted = False
                            for ml in block:
                                newb.append(ml)
                                if (not inserted) and ml.strip().startswith('.locals'):
                                    idx = total % count
                                    newb.append(f"    invoke-static {{}}, {helper_ref}->opaqueV{idx}()V")
                                    inserted = True
                                    per += 1
                                    total += 1
                                    changed = True
                            out.extend(newb)
                    else:
                        out.extend(block)
            else:
                out.append(line)
            i += 1
        if changed:
            new_text = '\n'.join(out)
            if dry_run:
                print(f"[dry-run] Would modify: {sf} (injections: {per})")
            else:
                sf.write_text(new_text, encoding='utf-8')
    print(f"Total injections: {total}")


def parse_args():
    p = argparse.ArgumentParser(description='Minimal inject helper + inject calls')
    p.add_argument('--dir', '-d', default='.', help='root dir containing smali tree')
    p.add_argument('--prefix', default='La/obf/junk', help='helper package prefix (no leading L required)')
    p.add_argument('--class-name', default='JunkHelper')
    p.add_argument('--count', type=int, default=20)

    p.add_argument('--mode', choices=['before_return', 'simple_call'], default='before_return')
    p.add_argument('--target', default=None, help='only inject into package prefix (dot or slash separated)')
    p.add_argument('--max-per-file', type=int, default=1)
    p.add_argument('--backup', action='store_true', help='create a directory copy before modifying files')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--force', action='store_true')
    return p.parse_args()


def main():
    args = parse_args()
    root = Path(args.dir)
    smali_dir = find_smali_dir(root)
    if args.backup and not args.dry_run:
        backup_dir = root.with_name(root.name + '_backup')
        if backup_dir.exists():
            print(f"Backup already exists: {backup_dir}")
        else:
            print(f"Creating backup: {backup_dir}")
            shutil.copytree(root, backup_dir)
    helper_text = build_helper(args.prefix, args.class_name, args.count)
    write_helper(smali_dir, args.prefix, args.class_name, helper_text, args.dry_run, force=args.force)
    # always perform injection after ensuring helper is present
    inject(smali_dir, args.prefix, args.class_name, args.count, args.mode, args.target, args.max_per_file, args.dry_run)


if __name__ == '__main__':
    main()
