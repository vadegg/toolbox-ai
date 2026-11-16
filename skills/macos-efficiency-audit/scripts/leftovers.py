#!/usr/bin/env python3
"""Data left behind by applications that are no longer installed.

Read-only. Usage: leftovers.py [--min-mb N] [--by-location] [--paths-out FILE] [--json]

How it decides: it collects the bundle identifiers and names of everything that
is still installed (application bundles found by Spotlight and in the usual
folders, Homebrew formulas and casks, a list of common command-line tools and
Apple internals), then walks the folders where macOS applications keep their
data (Application Support, Caches, Containers, Group Containers, Preferences,
logs, cookies, web storage, launch agents, plug-ins, privileged helpers) and
reports every entry whose owner it cannot match. Matching is deliberately
generous, so the list errs towards missing a leftover rather than naming a
live application. Read the list before acting on it: a generic name such as
"firestore" or "CEF" can belong to several apps.

  --min-mb N      list only owners whose total is at least N MB (default 1); the
                  smaller ones are still counted
  --by-location   group by folder instead of by inferred owner
  --paths-out F   write every unmatched path, one per line, for trash.sh --from
"""
import argparse
import glob
import json
import os
import plistlib
import re
import subprocess
import sys

HOME = os.path.expanduser("~")

APP_GLOBS = [
    "/Applications/*.app", "/Applications/*/*.app", "/Applications/*/*/*.app",
    f"{HOME}/Applications/*.app", f"{HOME}/Applications/*/*.app", f"{HOME}/Applications/*/*/*.app",
    "/System/Applications/*.app", "/System/Applications/Utilities/*.app",
    "/System/Library/CoreServices/*.app", "/System/Library/CoreServices/Applications/*.app",
    "/Library/Application Support/*/*.app", "/Library/Application Support/*/*/*.app",
    "/opt/*.app", "/opt/*/*.app", "/opt/*/*/*.app", "/usr/local/*.app", "/usr/local/*/*.app",
    f"{HOME}/Library/Application Support/*/*.app", f"{HOME}/Library/Application Support/*/*/*.app",
    "/opt/homebrew/Caskroom/*/*/*.app", "/opt/homebrew/Cellar/*/*/*.app", "/opt/homebrew/Cellar/*/*/*/*.app",
    "/usr/local/Caskroom/*/*/*.app",
]

# Things that legitimately own a folder without being an .app bundle.
KNOWN_NAMES = """
pip uv npm npx node yarn pnpm bun deno git gh nvim neovim vim tmux docker colima lima ollama
python jupyter ipython matplotlib huggingface pipx poetry conda miniconda homebrew brew claude
claude-code codex gemini cursor code vscode google microsoft adobe jetbrains iterm iterm2 mozilla
firefox ms-playwright playwright puppeteer pandoc tesseract powershell dotnet nuget gnupg ssh tex
texlive fontconfig kubectl helm minikube terraform aws gcloud azure
crashreporter dock finder terminal addressbook audio autosave information fonts keychains mail
messages safari sync services icloud clouddocs accounts calendars reminders notes photos music
spotlight screen time syncedpreferences suggestions metadata passes shortcuts weather stocks
news maps family assistant siri biome duetexpertcenter daemon containers application scripts
knowledge differentialprivacy callhistorydb callhistorytransactions animoji icdd stickersd tipsd
homeenergyd videosubscriptionsd appplaceholdersyncd locationaccessstored sesstorage geoservices
cloudkit passkit gamekit energykit siritts amsdatamigratortool askpermissiond mbuseragent
desktop_sdk_macos_exe diagnostics_agent diag-plugin knowledge-agent replayd pbs sharedfilelistd
siriknowledged corespotlightd contextstoreagent scopedbookmarkagent minilauncher tokenbucketratelimiter
avatar cache index loginwindow com.apple caches cookies webkit httpstorages default.store
temporaryitems jetpackcache flutter_engine statsig-cache telemetrysignalcache ssu
io.sentry sentrycrash segment com.datadoghq com.hackemist.sdimagecache com.plausiblelabs
launchdarkly telemetrydeck com.segment com.launchdarkly org.sparkle-project com.electron
systemconfiguration opendirectory directoryservice xsan systemmigrationd org.cups cups
bin lib lib64 include share libexec sbin etc var opt cellar caskroom frameworks
diagnosticreports crashreporter node-gyp cef chromium electron
"""


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def run(cmd, timeout=120):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def installed():
    paths = set(l for l in run(["mdfind", "kMDItemContentType == 'com.apple.application-bundle'"], 180).splitlines() if l)
    for g in APP_GLOBS:
        paths.update(glob.glob(g))
    bids, names = set(), set()
    for a in paths:
        if a.startswith("/Volumes/") or "/.Trash/" in a:
            continue
        names.add(norm(os.path.basename(a)[:-4]))
        try:
            with open(os.path.join(a, "Contents", "Info.plist"), "rb") as f:
                p = plistlib.load(f)
            if p.get("CFBundleIdentifier"):
                bids.add(p["CFBundleIdentifier"].lower())
            if p.get("CFBundleName"):
                names.add(norm(p["CFBundleName"]))
        except Exception:
            pass
    for cmd in (["brew", "list", "--formula"], ["brew", "list", "--cask"]):
        names.update(norm(x) for x in run(cmd).split())
    for pkg in run(["pkgutil", "--pkgs"]).split():
        if not pkg.startswith("com.apple."):
            bids.add(pkg.lower())
            names.update(norm(c) for c in pkg.split(".")[2:] if len(c) >= 4)
    names.update(norm(x) for x in KNOWN_NAMES.split())
    names.discard("")
    return bids, names


def matcher(bids, names):
    skip = ("com.apple.", "com.apple", "loginwindow", "group.com.apple", "systemgroup.com.apple")

    def matches(key):
        k = key.lower()
        if k.startswith(skip):
            return "apple"
        kk = re.sub(r"^(group|systemgroup)\.", "", k)
        m = re.match(r"^[A-Z0-9]{10}\.(.+)$", key)       # team-id prefixed group container
        if m:
            kk = re.sub(r"^(group|systemgroup)\.", "", m.group(1).lower())
        for b in bids:
            if kk == b or kk.startswith(b + ".") or b.startswith(kk + "."):
                return "bundle id"
        nk = norm(kk)
        if not nk:
            return "empty"
        for n in names:
            if nk == n:
                return "name"
            if len(n) >= 5 and (nk.startswith(n) or nk.endswith(n)):
                return "name"
            if len(nk) >= 5 and (n.startswith(nk) or n.endswith(nk)):
                return "name"
        if len(nk) >= 4:
            for b in bids:
                for comp in b.split("."):
                    c = norm(comp)
                    if c == nk or (len(nk) >= 5 and c.startswith(nk)):
                        return "component"
        parts = [p for p in re.split(r"[.\-_ ]", kk) if p]
        if parts:
            last = norm(parts[-1])
            if len(last) >= 4 and last in names:
                return "token"
            if len(parts) >= 2:
                vendor = ".".join(parts[:2])
                for b in bids:
                    if b.startswith(vendor + "."):
                        return "vendor"
        if os.path.exists(f"/usr/libexec/{key}") or os.path.exists(f"/usr/sbin/{key}"):
            return "apple daemon"
        return None
    return matches


LOCATIONS = [
    ("~/Library/Application Support", f"{HOME}/Library/Application Support"),
    ("~/Library/Caches", f"{HOME}/Library/Caches"),
    ("~/Library/Containers", f"{HOME}/Library/Containers"),
    ("~/Library/Group Containers", f"{HOME}/Library/Group Containers"),
    ("~/Library/Preferences", f"{HOME}/Library/Preferences"),
    ("~/Library/Preferences/ByHost", f"{HOME}/Library/Preferences/ByHost"),
    ("~/Library/Saved Application State", f"{HOME}/Library/Saved Application State"),
    ("~/Library/Logs", f"{HOME}/Library/Logs"),
    ("~/Library/HTTPStorages", f"{HOME}/Library/HTTPStorages"),
    ("~/Library/WebKit", f"{HOME}/Library/WebKit"),
    ("~/Library/Cookies", f"{HOME}/Library/Cookies"),
    ("~/Library/Application Scripts", f"{HOME}/Library/Application Scripts"),
    ("~/Library/LaunchAgents", f"{HOME}/Library/LaunchAgents"),
    ("~/Library/Internet Plug-Ins", f"{HOME}/Library/Internet Plug-Ins"),
    ("~/Library/PreferencePanes", f"{HOME}/Library/PreferencePanes"),
    ("~/Library/Services", f"{HOME}/Library/Services"),
    ("~/Library/QuickLook", f"{HOME}/Library/QuickLook"),
    ("~/Library/Input Methods", f"{HOME}/Library/Input Methods"),
    ("~/Library/Audio/Plug-Ins/HAL", f"{HOME}/Library/Audio/Plug-Ins/HAL"),
    ("/Library/Application Support", "/Library/Application Support"),
    ("/Library/Preferences", "/Library/Preferences"),
    ("/Library/PrivilegedHelperTools", "/Library/PrivilegedHelperTools"),
    ("/Library/LaunchAgents", "/Library/LaunchAgents"),
    ("/Library/LaunchDaemons", "/Library/LaunchDaemons"),
    ("/Library/Internet Plug-Ins", "/Library/Internet Plug-Ins"),
    ("/Library/Input Methods", "/Library/Input Methods"),
    ("/Library/PreferencePanes", "/Library/PreferencePanes"),
    ("/Library/QuickLook", "/Library/QuickLook"),
    ("/Library/Audio/Plug-Ins/HAL", "/Library/Audio/Plug-Ins/HAL"),
    ("/Library/Frameworks", "/Library/Frameworks"),
    ("/Library/Caches", "/Library/Caches"),
    ("/Library/Logs", "/Library/Logs"),
    ("/usr/local", "/usr/local"),
    ("/opt", "/opt"),
    ("~ (hidden folders)", HOME),
]
# Hidden folders every shell or tool leaves at home; never leftovers.
HOME_SKIP = {".Trash", ".ssh", ".config", ".local", ".cache", ".zsh_sessions", ".git", ".gnupg",
             ".cups", ".CFUserTextEncoding", ".DS_Store", ".bash_sessions", ".vim", ".npm", ".docker",
             ".codex", ".claude", ".gemini", ".cursor", ".vscode", ".vscode-server", ".agents", ".ollama",
             ".colima", ".lima", ".cargo", ".rustup", ".gradle", ".m2", ".pyenv", ".nvm", ".bun", ".go",
             ".matplotlib", ".ipython", ".jupyter", ".pip", ".tmp", ".Trashes", ".android", ".huggingface"}
SUFFIXES = (".plist", ".savedState", ".binarycookies", ".app", ".bundle", ".prefPane",
            ".qlgenerator", ".kext", ".framework", ".driver", ".log", ".lockfile", ".plugin")


def du_kb(path):
    out = run(["du", "-sk", path])
    try:
        return int(out.split()[0])
    except (IndexError, ValueError):
        return 0


def owner_of(entry):
    key = entry
    for s in SUFFIXES:
        if key.endswith(s):
            key = key[: -len(s)]
    key = re.sub(r"\.[0-9A-Fa-f-]{36}$", "", key)          # ByHost UUID
    key = re.sub(r"^[A-Z0-9]{10}\.", "", key)              # team id
    key = re.sub(r"^(group|systemgroup)\.", "", key)
    parts = [p for p in re.split(r"[.]", key) if p]
    if len(parts) >= 3 and parts[0].lower() in {"com", "org", "net", "io", "app", "ai", "ru", "co", "me", "in", "nl", "de", "us", "tech", "company", "su", "now", "md", "wtf"}:
        return norm(parts[2]) or norm(parts[1])
    if len(parts) == 2 and parts[0].lower() in {"com", "org", "net", "io", "app", "ai", "ru", "co"}:
        return norm(parts[1])
    return norm(parts[0]) if parts else norm(key)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min-mb", type=float, default=1.0)
    ap.add_argument("--by-location", action="store_true")
    ap.add_argument("--paths-out")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    bids, names = installed()
    matches = matcher(bids, names)
    print(f"# installed: {len(bids)} bundle ids, {len(names)} names", file=sys.stderr)

    found = []
    for label, d in LOCATIONS:
        if not os.path.isdir(d):
            continue
        try:
            entries = sorted(os.listdir(d))
        except PermissionError:
            print(f"# {label}: permission denied (Full Disk Access needed)", file=sys.stderr)
            continue
        for e in entries:
            if d == HOME:
                if not e.startswith(".") or e in HOME_SKIP or not os.path.isdir(os.path.join(d, e)):
                    continue
                e_key = e[1:]
            elif e.startswith("."):
                continue
            else:
                e_key = e
            key = e_key
            for s in SUFFIXES:
                if key.endswith(s):
                    key = key[: -len(s)]
            key = re.sub(r"\.[0-9A-Fa-f-]{36}$", "", key)
            if matches(key):
                continue
            path = os.path.join(d, e)
            try:
                owner = os.stat(path).st_uid == os.getuid()
            except OSError:
                owner = False
            found.append({"location": label, "entry": e, "path": path, "kb": du_kb(path),
                          "owner": owner_of(e_key), "mine": owner})

    if a.paths_out:
        with open(a.paths_out, "w", encoding="utf-8") as f:
            for r in found:
                f.write(r["path"] + "\n")
    if a.json:
        print(json.dumps(found, indent=1, ensure_ascii=False))
        return

    total = sum(r["kb"] for r in found)
    print(f"Unmatched entries: {len(found)}, {total / 1048576:.2f} GiB in total\n")
    if a.by_location:
        groups = {}
        for r in found:
            groups.setdefault(r["location"], []).append(r)
        for loc, rows in groups.items():
            print(f"## {loc}: {len(rows)} entries, {sum(x['kb'] for x in rows) / 1024:.1f} MiB")
            for r in sorted(rows, key=lambda x: -x["kb"]):
                print(f"  {r['kb'] / 1024:9.1f} MiB  {r['entry']}{'' if r['mine'] else '  [root-owned]'}")
        return

    owners = {}
    for r in found:
        owners.setdefault(r["owner"], []).append(r)
    ranked = sorted(owners.items(), key=lambda kv: -sum(x["kb"] for x in kv[1]))
    small = 0
    print("## By inferred owner (largest first)")
    for owner, rows in ranked:
        kb = sum(x["kb"] for x in rows)
        if kb / 1024 < a.min_mb:
            small += 1
            continue
        print(f"\n{owner or '(unnamed)'}: {kb / 1024:.1f} MiB in {len(rows)} place(s)")
        for r in sorted(rows, key=lambda x: -x["kb"]):
            print(f"  {r['kb'] / 1024:9.1f} MiB  {r['location']}/{r['entry']}{'' if r['mine'] else '  [root-owned]'}")
    if small:
        print(f"\n(+ {small} owners under {a.min_mb:g} MiB each; rerun with --min-mb 0 or --by-location to see them)")


if __name__ == "__main__":
    main()
