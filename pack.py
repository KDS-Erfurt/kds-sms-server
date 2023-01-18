import subprocess
from pathlib import Path

from classes.Static import STATIC

cwd = Path(__file__).parent
installer_path = cwd / "installer"
make_nsis_compiler_path = Path("C:/Program Files (x86)/NSIS/makensis.exe")
nsis_script_path = cwd / "installer.nsi"
nsis_output_path = installer_path / "installer.exe"
output_path = installer_path / f"SmsServerSetup-" \
                               f"{STATIC.version.replace('.', '-')}-{STATIC.state}-{STATIC.build_number}.exe"

if __name__ == '__main__':
    if not make_nsis_compiler_path.exists():
        raise FileNotFoundError(f"Could not find NSIS compiler at {make_nsis_compiler_path}")

    if not nsis_script_path.exists():
        raise FileNotFoundError(f"Could not find NSIS script at {nsis_script_path}")

    if nsis_output_path.exists():
        nsis_output_path.unlink()

    subprocess.run([make_nsis_compiler_path, nsis_script_path])

    if not nsis_output_path.exists():
        raise FileNotFoundError(f"Could not find NSIS output at {nsis_output_path}")

    if output_path.exists():
        output_path.unlink()

    nsis_output_path.rename(output_path)

    print(f"Installer created at {output_path}")
