# <img src="https://cdn.simpleicons.org/android" alt="Android" width="25"/> APM (Android Package Manager)  

<p>
    <a href="https://github.com/abhay-byte/apm/releases/latest">
        <img src="https://img.shields.io/github/v/release/abhay-byte/apm?style=flat" alt="Latest Release"/>
    </a>
    <a href="https://github.com/abhay-byte/apm/stargazers">
        <img src="https://img.shields.io/github/stars/abhay-byte/apm?style=flat" alt="GitHub Stars"/>
    </a>
    <a href="https://github.com/abhay-byte/apm/releases">
        <img src="https://img.shields.io/github/downloads/abhay-byte/apm/total?style=flat" alt="Total Downloads"/>
    </a>
</p>



**APM** is a lightweight, config-driven command-line tool for managing Free and Open Source Software (FOSS) Android applications. It integrates multiple F-Droid-compatible repositories, provides friendly package name mappings, and handles installation, updates, and curation with robust error handling. APM ensures all operations are driven solely by your configuration files—no hardcoded defaults.

-   **Focus:** Privacy, security, and ease of use for FOSS Android apps.
-   **Backend:** Powered by `fdroidcl` for repository management and `adb` for device interactions.
-   **Key Strength:** Fully customizable via YAML configs for repositories, mappings, and filters.


## Installation

1.  **Clone the Repository:**

    ```bash
    git clone https://github.com/yourusername/apm.git
    cd apm
    ```

2.  **Run the Installer:**

    ```bash
    chmod +x install.sh
    ./install.sh
    ```

3.  **Add to PATH (if needed):**

    ```bash
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    source ~/.bashrc
    ```

4.  **Verify:**

    ```bash
    apm --help
    apm repo-status
    ```

## Usage

APM provides a simple CLI interface. Run `apm --help` for full options.

### Core Commands

-   **Search for Packages:**

    ```bash
    apm search browser
    apm search --category Security
    ```

-   **Install a Package:**

    ```bash
    apm install firefox
    apm install --device emulator-5554 signal
    ```

-   **Batch Install:**

    ```bash
    apm batch-install essential_packages.txt
    ```

-   **Update Repositories and Packages:**

    ```bash
    apm update
    ```

-   **List Devices:**

    ```bash
    apm devices
    ```

-   **Manage Mappings:**

    ```bash
    apm mappings # List all mappings
    apm add-mapping myapp com.example.myapp
    apm remove-mapping myapp
    apm resolve firefox # Resolve alias to package ID
    apm list-categories # List mapping categories
    apm debug-mappings # Debug mappings
    ```

-   **Repository Management:**

    ```bash
    apm repo-status # Check connectivity
    apm repo-list # List configured repos
    ```

## Configuration

All settings are in `~/.config/apm/`:

-   **`config.yaml`** (required): Repositories, paths, filters, updates, etc.

    ```yaml
    repositories:
      - name: "F-Droid"
        url: "https://f-droid.org/repo"
        enabled: true
        priority: 1
        fingerprint: "43238D512C1E5EB2D6569F4A3AFBF5523418B82E0A3ED1552770ABB9A9C9CCAB"

    paths:
      cache_dir: "~/.cache/apm"
      download_dir: "~/.cache/apm/apks"

    filters:
      approved_licenses: ["GPL-3.0", "MIT"]
      blocked_anti_features: ["Ads", "Tracking"]

    updates:
      continue_on_repo_failure: true
    ```

-   **`package_mappings.yaml`** (required): Friendly names to package IDs.

    ```yaml
    browsers:
      firefox: "org.mozilla.fennec_fdroid"
      tor-browser: "org.torproject.torbrowser_alpha"
    ```

-   **`curation_config.yaml`** (optional): Advanced filters.

    ```yaml
    approved_licenses: ["GPL-3.0", "MIT"]
    min_target_sdk: 26
    ```

The installer auto-fixes any path inconsistencies (e.g., 'foss-pm' → 'apm').

## Troubleshooting

-   **Unreachable Repositories:**
    -   Run `apm repo-status` to check connectivity.
    -   Edit `config.yaml` to disable problematic repos (set `enabled: false`).
    -   Manual remove: `fdroidcl repo remove <url>` (e.g., `fdroidcl repo remove https://guardianproject.info/fdroid/repo`).
    -   If repo not found: It's already removed or never added—check with `fdroidcl repo list`.

-   **`fdroidcl` Errors:**
    -   Reinstall: `go install mvdan.cc/fdroidcl@latest`.
    -   List repos: `fdroidcl repo list`.
    -   Update manually: `fdroidcl update`.

-   **`apm` Command Not Found:**
    -   Ensure `~/.local/bin` is in your `PATH`.
    -   Run `source ~/.bashrc`.

-   **Other Issues:**
    -   Check logs in `~/.cache/apm/logs/apm.log`.
    -   Re-run installer: `./install.sh`.
    -   For network issues: Test with `curl -I https://f-droid.org/repo/index-v1.jar`.

## Contributing

1.  Fork the repo.
2.  Create a branch: `git checkout -b feature/awesome-feature`.
3.  Commit changes: `git commit -am 'Add awesome feature'`.
4.  Push: `git push origin feature/awesome-feature`.
5.  Submit a pull request.

We welcome contributions to mappings, configs, or code!

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

-   [fdroidcl](https://github.com/mvdan/fdroidcl) for repo management.
-   Inspired by F-Droid and community repositories.

---

*Happy managing your Android FOSS apps! 🤖📱*
