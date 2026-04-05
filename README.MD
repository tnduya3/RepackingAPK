# APK Repacking Tool

[![Python](https://img.shields.io/badge/Python-3.6+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A command-line tool for repacking Android APK files, featuring disassembly, rebuilding, signing, and optional code obfuscation to enhance security and modify APKs.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Requirements](#requirements)
- [Contributing](#contributing)
- [License](#license)

## Features

- **APK Disassembly and Rebuilding**: Decompile APKs to Smali code, modify as needed, and rebuild.
- **Automatic Signing**: Sign repacked APKs with custom keystores.
- **Code Obfuscation**: Optional junk code injection and class renaming for anti-reverse engineering.
- **Batch Processing**: Handle multiple APKs in a single run.
- **Interactive Mode**: User-friendly prompts for configuration.
- **Automated Tool Installation**: Scripts to install required dependencies (JDK, apktool).

## Installation

### Prerequisites

- **Python 3.6 or higher**: Download from [python.org](https://www.python.org/downloads/).
- **Windows Package Manager (winget)**: Included in Windows 10/11 (recommended for automatic JDK installation).

### Steps

1. Clone or download this repository.

2. Run the installation script to set up dependencies:

   ```bash
   python install.py
   ```

   This script automatically:
   - Detects and installs the Java Development Kit (JDK) if missing.
   - Downloads and configures apktool.
   - Verifies availability of keytool and jarsigner.

   If automatic installation fails, follow the on-screen prompts for manual setup.

## Usage

### Command-Line Interface

#### Basic Repacking

Repack a single APK file:

```bash
python repacking.py input.apk keystore.jks output.apk
```

- `input.apk`: Path to the source APK.
- `keystore.jks`: Keystore file for signing.
- `output.apk`: Destination for the signed APK.

#### Interactive Mode

For guided setup:

```bash
python repacking.py
```

Prompts will guide you through:
- Selecting single or multiple input APKs.
- Entering keystore credentials (alias, passwords).
- Configuring output directories.
- Enabling obfuscation options.

### Advanced Options

- **Obfuscation**: Inject junk code and rename classes to obscure the APK's structure.
- **Keystore Management**: Create new keystores or use existing ones.
- **Batch Mode**: Process multiple APKs with automatic output naming.

### Example

Repack an APK with obfuscation enabled (via interactive prompts):

```bash
python repacking.py
# Follow prompts: select input, enable obfuscation, provide keystore details.
```

## Requirements

- **Python 3.6+**
- **JDK 8+** (for keytool and jarsigner)
- **apktool** (for APK manipulation)

All dependencies are installed via `install.py`.

## Contributing

Contributions are welcome! Please:

1. Fork the repository.
2. Create a feature branch.
3. Submit a pull request with a clear description of changes.

For issues or suggestions, open a GitHub issue.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.