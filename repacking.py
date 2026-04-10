import os
import sys
import subprocess
import shutil
from multiprocessing import Pool, cpu_count


def find_tool(name):
    # check PATH
    p = shutil.which(name)
    if p:
        return p
    # check current directory
    if os.path.isfile(name):
        return os.path.abspath(name)
    # fallback: look for jar filename
    if name == 'apktool':
        if os.path.isfile('apktool.jar'):
            return 'java -jar ' + os.path.abspath('apktool.jar')
    return None


def run(cmd, shell=False):
    print('> ' + (cmd if isinstance(cmd, str) else ' '.join(cmd)))
    try:
        if shell or isinstance(cmd, str):
            subprocess.check_call(cmd, shell=True)
        else:
            subprocess.check_call(cmd)
        return True
    except subprocess.CalledProcessError as e:
        print('[-] Command failed: {}'.format(e))
        return False


def apktool_disassemble(apktool_cmd, apk_path, out_dir):
    cmd = []
    if apktool_cmd.startswith('java -jar'):
        cmd = apktool_cmd.split() + ['d', apk_path, '-o', out_dir]
    else:
        cmd = [apktool_cmd, 'd', apk_path, '-o', out_dir]
    return run(cmd)


def apktool_build(apktool_cmd, project_dir):
    cmd = []
    if apktool_cmd.startswith('java -jar'):
        cmd = apktool_cmd.split() + ['b', project_dir]
    else:
        cmd = [apktool_cmd, 'b', project_dir]
    return run(cmd)


def jarsigner_sign(jarsigner_cmd, keystore, storepass, keypass, alias, unsigned_apk, out_apk=None):
    # if out_apk is provided, use -signedjar to produce the output file
    if out_apk:
        cmd = [jarsigner_cmd, '-keystore', keystore, '-storepass', storepass, '-keypass', keypass, '-signedjar', out_apk, unsigned_apk, alias]
    else:
        cmd = [jarsigner_cmd, '-keystore', keystore, '-storepass', storepass, '-keypass', keypass, unsigned_apk, alias]
    return run(cmd)


def find_built_apk(project_dir):
    dist = os.path.join(project_dir, 'dist')
    if not os.path.isdir(dist):
        return None
    files = [f for f in os.listdir(dist) if f.endswith('.apk')]
    if not files:
        return None
    return os.path.join(dist, files[0])


def keytool_create(keytool_cmd, keystore_path, alias, storepass, keypass, dname=None, validity=3650):
    # create keytool command
    cmd = [keytool_cmd, '-genkeypair', '-alias', alias, '-keyalg', 'RSA', '-keysize', '2048', '-keystore', keystore_path,
           '-storepass', storepass, '-keypass', keypass, '-validity', str(validity)]
    if dname:
        cmd += ['-dname', dname]
    return run(cmd)


def run_obfuscation_commands(project_dir, inject_mode='before_return', do_rename=True, rename_prefix='La/obf', rename_rename_files=False, rename_dryrun=False, helper_prefix=None):
    import sys
    python_exec = sys.executable
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cls = os.path.join(script_dir, 'class_rename.py')
    inj = os.path.join(script_dir, 'inject_junk.py')

    ok = True

    # determine helper prefix (derived from rename_prefix if not provided)
    if helper_prefix is None:
        helper_prefix = rename_prefix.lstrip('L').strip('/') + '/junk'

    # run inject_junk first (so helper gets injected and will be renamed by class_rename)
    if os.path.isfile(inj):
        cmd_inj = [python_exec, inj, '--dir', project_dir, '--mode', inject_mode, '--prefix', helper_prefix, '--force']
        print(f"[obf] Injecting helper first: {' '.join(cmd_inj)}")
        ok = ok and run(cmd_inj)
    else:
        print(f"[obf] inject_junk.py not found at {inj}")
        ok = False

    # run class_rename if requested
    if do_rename:
        if os.path.isfile(cls):
            cmd1 = [python_exec, cls, '--dir', project_dir, '--prefix', rename_prefix, '--out-mapping', os.path.join(project_dir, 'mappings', 'class_mapping.txt')]
            if rename_rename_files:
                cmd1.append('--rename-files')
            if rename_dryrun:
                cmd1.append('--dry-run')
            print(f"[obf] Running: {' '.join(cmd1)}")
            ok = ok and run(cmd1)
        else:
            print(f"[obf] class_rename.py not found at {cls}")
            ok = False
    else:
        print('[obf] Skipping class rename as requested.')

    return ok


def _prompt_input_paths(single):
    import shlex
    if single:
        while True:
            p = input('Enter path to input (APK or project dir): \n').strip()
            if os.path.exists(p):
                return [p]
            print('[-] Path not found, try again.')
    else:
        while True:
            line = input('Enter paths (space-separated, quote paths with spaces): \n').strip()
            try:
                parts = shlex.split(line)
            except Exception:
                parts = [p for p in line.split(' ') if p]
            missing = [p for p in parts if not os.path.exists(p)]
            if missing:
                print('[-] These paths were not found: {}'.format(', '.join(missing)))
                continue
            return parts


def process_single_input(inp, keystore, storepass, keypass, alias, out_dir, output, apktool_cmd, jarsigner_cmd, obfuscate=False, inject_mode='before_return', do_rename=True, rename_prefix='La/obf', rename_rename_files=False, rename_dryrun=False, helper_prefix=None):
    if not os.path.exists(inp):
        print('[-] Input not found: {}'.format(inp))
        return

    # determine project dir
    if os.path.isdir(inp):
        project_dir = inp
        print('[*] Using directory input: {}'.format(project_dir))
    else:
        if not inp.endswith('.apk'):
            print('[-] Skipping unknown input type: {}'.format(inp))
            return
        project_dir = inp[:-4] + '_out'
        if os.path.isdir(project_dir):
            print('[*] Found existing directory {}, skipping disassemble.'.format(project_dir))
        else:
            print('[*] Disassembling {} -> {}'.format(inp, project_dir))
            if not apktool_disassemble(apktool_cmd, inp, project_dir):
                print('[-] Failed to disassemble {}; skipping.'.format(inp))
                return

    # obfuscation
    if obfuscate:
        print('[*] Running obfuscation steps...')
        ok = run_obfuscation_commands(project_dir, inject_mode=inject_mode, do_rename=do_rename, rename_prefix=rename_prefix, rename_rename_files=rename_rename_files, rename_dryrun=rename_dryrun, helper_prefix=helper_prefix)
        if not ok:
            print('[-] Obfuscation steps reported failures; continuing to build anyway.')

    # build
    print('[*] Building project {}...'.format(project_dir))
    if not apktool_build(apktool_cmd, project_dir):
        print('[-] apktool build failed for {}; skipping.'.format(project_dir))
        return

    unsigned_apk = find_built_apk(project_dir)
    if not unsigned_apk:
        print('[-] Could not find built APK in {}/dist'.format(project_dir))
        return
    print('[*] Built APK: {}'.format(unsigned_apk))

    # determine output path
    multiple = out_dir is not None
    if multiple:
        # normalize path first to handle trailing slashes so basename() returns the expected name
        base = os.path.splitext(os.path.basename(os.path.normpath(inp)))[0]
        final_out = os.path.join(out_dir, base + '-signed.apk')
        # avoid overwriting files when multiple inputs produce the same base name
        if os.path.exists(final_out):
            i = 1
            while True:
                candidate = os.path.join(out_dir, f"{base}-signed-{i}.apk")
                if not os.path.exists(candidate):
                    final_out = candidate
                    break
                i += 1
    else:
        final_out = output

    # sign
    print('[*] Signing {} -> {}'.format(unsigned_apk, final_out))
    if not jarsigner_sign(jarsigner_cmd, keystore, storepass, keypass, alias, unsigned_apk, final_out):
        print('[-] Signing failed for {}; skipping.'.format(unsigned_apk))
        return

    print('[+] Done: {}'.format(final_out))


def main():
    import shlex
    import getpass

    if len(sys.argv) == 1:
        print('[*] Interactive mode')
        # choose input mode
        while True:
            mode = input('Choose input mode: [1] Single input  [2] Multiple inputs (1/2): \n').strip()
            if mode in ('1', '2'):
                break
        single = mode == '1'

        inputs = _prompt_input_paths(single)

        # keystore option
        while True:
            kopt = input('Keystore option: [1] Use existing keystore  [2] Create new keystore with keytool (1/2): \n').strip()
            if kopt in ('1', '2'):
                break

        if kopt == '1':
            while True:
                keystore = input('Enter path to existing keystore file: \n').strip()
                if os.path.exists(keystore):
                    break
                print('[-] Keystore not found, try again.')
            alias = input('Enter key alias (default: g11): \n').strip() or 'g11'
            storepass = getpass.getpass('Enter keystore storepass: \n').strip()
            if not storepass:
                storepass = '001578'
            keypass = getpass.getpass('Enter key password (press Enter to use same as storepass): \n').strip()
            if not keypass:
                keypass = storepass
        else:
            keytool_cmd = find_tool('keytool')
            if not keytool_cmd:
                print('[-] keytool not found in PATH. Cannot create keystore.')
                sys.exit(1)
            keystore = input('Enter output path for new keystore (e.g., mykeystore.keystore): \n').strip()
            alias = input('Enter alias for new key (default: g11): \n').strip() or 'g11'
            storepass = getpass.getpass('Enter storepass for new keystore: \n').strip()
            if not storepass:
                storepass = '001578'
            keypass = getpass.getpass('Enter keypass for new key (press Enter to use same as storepass): \n').strip()
            if not keypass:
                keypass = storepass
            dname = input('Enter DName for certificate (press Enter to use default): \n').strip()
            if not dname:
                dname = 'CN=Malware,OU=UIT,O=UIT,L=HCM,ST=HCM,C=VN'

            print('[*] Creating keystore {}...'.format(keystore))
            if not keytool_create(keytool_cmd, keystore, alias, storepass, keypass, dname=dname):
                print('[-] Failed to create keystore.')
                sys.exit(1)
            print('[+] Keystore created: {}'.format(keystore))

        # output selection
        if len(inputs) > 1:
            while True:
                out_dir = input('Enter output directory to store signed APKs: \n').strip()
                if out_dir.endswith('.apk'):
                    print('[*] Treating provided output as directory and creating: {}'.format(out_dir + '.dir'))
                    out_dir = out_dir + '.dir'
                if not os.path.exists(out_dir):
                    try:
                        os.makedirs(out_dir)
                        break
                    except Exception as e:
                        print('[-] Failed to create directory: {}'.format(e))
                else:
                    break
            output = None
        else:
            out = input('Enter output file path or directory (if directory, signed apk will be placed inside): \n').strip()
            if os.path.isdir(out):
                out_dir = out
                output = None
            else:
                out_dir = None
                output = out

    else:
        # non-interactive (backwards compatible)
        if len(sys.argv) < 4:
            print('Usage: {} <input1> [<input2> ...] <keystore_path> <output>'.format(sys.argv[0]))
            sys.exit(1)

        parts = sys.argv[1:]
        keystore = parts[-2]
        output = parts[-1]
        inputs = parts[:-2]

        if not os.path.exists(keystore):
            print('[-] Keystore not found: {}'.format(keystore))
            sys.exit(1)

        # default alias/password as before
        alias = 'g11'
        storepass = '001578'
        keypass = '001578'

        # determine out_dir for multiple
        multiple = len(inputs) > 1
        if multiple:
            out_dir = output
            if out_dir.endswith('.apk'):
                print('[*] Multiple inputs detected; treating output `{}` as a directory and creating it.'.format(output))
                out_dir = output + '.dir'
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)
        else:
            if os.path.isdir(output):
                out_dir = output
            else:
                out_dir = None

    apktool_cmd = find_tool('apktool')
    jarsigner_cmd = find_tool('jarsigner')

    if not apktool_cmd:
        print('[-] apktool not found in PATH or current directory (or apktool.jar).')
        sys.exit(1)
    if not jarsigner_cmd:
        print('[-] jarsigner not found in PATH or current directory.')
        sys.exit(1)

    multiple = len(inputs) > 1

    # if multiple inputs, make sure out_dir is set
    if multiple:
        try:
            out_dir
        except NameError:
            print('[-] Output directory not specified for multiple inputs.')
            sys.exit(1)

    # set obfuscation options (only in interactive mode)
    obfuscate = False
    inject_mode = 'before_return'
    do_rename = True
    rename_prefix = 'La/obf'
    rename_rename_files = False
    rename_dryrun = False
    helper_prefix = None
    if len(sys.argv) == 1:  # interactive
        try:
            ans = input('Run obfuscation steps before build? [y/N]: \n').strip().lower()
        except (EOFError, KeyboardInterrupt):
            ans = 'n'
        if ans.startswith('y'):
            try:
                mode = input('Inject mode (before_return/simple_call) [before_return]: \n').strip() or 'before_return'
            except (EOFError, KeyboardInterrupt):
                mode = 'before_return'
            inject_mode = mode

            # prompt for class rename options
            try:
                rn = input('Run class rename? [Y/n]: \n').strip().lower()
            except (EOFError, KeyboardInterrupt):
                rn = 'y'
            if rn == '' or rn.startswith('y'):
                try:
                    prefix = input('Class rename prefix (default: La/obf): \n').strip() or 'La/obf'
                except (EOFError, KeyboardInterrupt):
                    prefix = 'La/obf'
                try:
                    rf = input('Rename class files on disk? [y/N]: \n').strip().lower()
                except (EOFError, KeyboardInterrupt):
                    rf = 'n'
                rename_files_flag = rf.startswith('y')
                try:
                    dr = input('Dry-run rename only? [y/N]: \n').strip().lower()
                except (EOFError, KeyboardInterrupt):
                    dr = 'n'
                rename_dryrun = dr.startswith('y')
                # derive helper prefix and optionally override
                helper_default = prefix.lstrip('L').strip('/') + '/junk'
                try:
                    hp = input(f'Helper prefix (default: {helper_default}): \n').strip()
                except (EOFError, KeyboardInterrupt):
                    hp = ''
                helper_prefix = hp or helper_default
                do_rename = True
            else:
                do_rename = False
                prefix = 'La/obf'
                rename_files_flag = False
                rename_dryrun = False
                helper_prefix = None
            rename_prefix = prefix
            rename_rename_files = rename_files_flag
            obfuscate = True

    if len(inputs) == 1:
        process_single_input(inputs[0], keystore, storepass, keypass, alias, out_dir, output, apktool_cmd, jarsigner_cmd, obfuscate, inject_mode, do_rename, rename_prefix, rename_rename_files, rename_dryrun, helper_prefix)
    else:
        with Pool(processes=min(len(inputs), cpu_count())) as pool:
            pool.starmap(process_single_input, [(inp, keystore, storepass, keypass, alias, out_dir, output, apktool_cmd, jarsigner_cmd, obfuscate, inject_mode, do_rename, rename_prefix, rename_rename_files, rename_dryrun, helper_prefix) for inp in inputs])


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("User interrupted! Exiting...")
        sys.exit(0)
