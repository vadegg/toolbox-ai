#!/usr/bin/env python3
"""What starts at login and what state it is in.

Read-only. Usage: launchd_audit.py [--json]

Covers the three plist folders (user agents, system agents, system daemons),
the classic Login Items list, Background Task Management's own record
(`sfltool dumpbtm`) and mounted disk images. For every plist it answers:
does the program still exist, is it loaded now, did the user already switch
it off in System Settings > Login Items, and when does it run.

Verdicts:
  DEAD          the program the plist points at no longer exists
  off (user)    Login Items shows it switched off ("disallowed" in BTM)
  disabled      disabled through launchctl
  running       loaded with a live process
  loaded        loaded, waits for its schedule or trigger
  not loaded    file present, nothing loaded it
"""
import argparse
import glob
import json
import os
import plistlib
import re
import shutil
import subprocess
import urllib.parse

HOME = os.path.expanduser("~")
DIRS = [
    ("user agent", os.path.join(HOME, "Library/LaunchAgents")),
    ("system agent", "/Library/LaunchAgents"),
    ("system daemon", "/Library/LaunchDaemons"),
]


def run(cmd, timeout=30):
    """Run a command and return stdout; an empty string when it hangs or is missing.

    `sfltool dumpbtm` has been seen to hang for minutes on some machines, and this
    audit must never wait on it: the report says "BTM state not measured" instead."""
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except subprocess.TimeoutExpired:
        print(f"# timed out after {timeout}s: {' '.join(cmd)} (reported as not measured)", file=__import__('sys').stderr)
        return ""
    except FileNotFoundError:
        return ""


def loaded_user_jobs():
    jobs = {}
    for line in run(["launchctl", "list"]).splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) == 3:
            jobs[parts[2]] = parts[0]
    return jobs


def disabled_overrides():
    out = run(["launchctl", "print-disabled", f"gui/{os.getuid()}"]) + run(["launchctl", "print-disabled", "system"])
    return set(re.findall(r'"([^"]+)" => disabled', out))


def btm_records():
    """Map plist path (and app bundle path) -> BTM disposition text."""
    out = run(["sfltool", "dumpbtm"], timeout=45)
    records, current = {}, {}
    for line in out.splitlines():
        line = line.strip()
        if re.match(r"^#\d+:$", line):
            current = {}
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        current[key] = value
        if key == "URL" and value.startswith("file://"):
            path = urllib.parse.unquote(value[len("file://"):]).rstrip("/")
            records[path] = current
    return records


def stale_btm(btm):
    """BTM records that still point at an application bundle which no longer exists."""
    stale = []
    for path, rec in btm.items():
        if rec.get("Type", "").startswith(("app", "login item")) and path.endswith(".app") and not os.path.exists(path):
            stale.append({"name": rec.get("Name", "?"), "path": path, "disposition": rec.get("Disposition", "")})
    return stale


def disposition(rec):
    if not rec:
        return ""
    d = rec.get("Disposition", "")
    if "disallowed" in d:
        return "off (user)"
    if "allowed" in d:
        return "allowed"
    return d


def schedule(p):
    s = []
    if p.get("RunAtLoad"):
        s.append("at login")
    if p.get("KeepAlive"):
        s.append("keep alive")
    if "StartInterval" in p:
        s.append(f"every {int(p['StartInterval']) // 60} min")
    if "StartCalendarInterval" in p:
        cal = p["StartCalendarInterval"]
        cal = cal if isinstance(cal, list) else [cal]
        s.append("at " + ", ".join(f"{c.get('Hour', '*')}:{int(c.get('Minute', 0)):02d}" for c in cal))
    if "WatchPaths" in p or "QueueDirectories" in p:
        s.append("on file change")
    if "Sockets" in p:
        s.append("on connection")
    if "MachServices" in p:
        s.append("on demand")
    return ", ".join(s) or "manual"


def audit_plists(jobs, disabled, btm):
    rows = []
    for kind, d in DIRS:
        for f in sorted(glob.glob(os.path.join(d, "*.plist"))):
            try:
                with open(f, "rb") as fh:
                    p = plistlib.load(fh)
            except Exception as err:  # unreadable plist is itself a finding
                rows.append({"kind": kind, "file": f, "label": "?", "program": "", "verdict": f"unreadable: {err}"})
                continue
            args = p.get("ProgramArguments") or []
            prog = p.get("Program") or (args[0] if args else "")
            if prog.startswith(("/", "~")):
                exists = os.path.exists(os.path.expanduser(prog))
            else:
                exists = bool(shutil.which(prog)) if prog else None
            label = p.get("Label", os.path.basename(f)[:-6])
            rec = btm.get(f)
            dispo = disposition(rec)
            if not prog:
                verdict = "stub (no program)"
            elif exists is False:
                verdict = "DEAD"
            elif dispo == "off (user)":
                verdict = "off (user)"
            elif label in disabled:
                verdict = "disabled"
            elif label in jobs and jobs[label] != "-":
                verdict = f"running pid {jobs[label]}"
            elif label in jobs:
                verdict = "loaded"
            elif kind == "system daemon":
                state = run(["launchctl", "print", f"system/{label}"])
                pid = re.search(r"^\s*pid = (\d+)", state, re.M)
                verdict = f"running pid {pid.group(1)}" if pid else ("loaded (system)" if "state =" in state else "not loaded")
            else:
                verdict = "not loaded"
            app = ""
            m = re.match(r"^(/.*?\.app)/", prog)
            if m and not os.path.exists(m.group(1)):
                app = "app bundle missing"
            rows.append({
                "kind": kind, "file": f, "label": label, "program": prog,
                "args": " ".join(args[1:4])[:80], "exists": exists, "schedule": schedule(p),
                "btm": dispo, "verdict": verdict, "note": app,
            })
    return rows


def login_items():
    names = run(["osascript", "-e", 'tell application "System Events" to get the name of every login item']).strip()
    paths = run(["osascript", "-e", 'tell application "System Events" to get the path of every login item']).strip()
    items = []
    if names:
        for n, p in zip(names.split(", "), paths.split(", ")):
            p = p.strip()
            missing = p == "missing value" or (p.startswith("/") and not os.path.exists(p))
            items.append({"name": n.strip(), "path": p, "stale": missing})
    return items


def mounted_images():
    out = run(["hdiutil", "info"])
    return [l.split(":", 1)[1].strip() for l in out.splitlines() if l.strip().startswith("image-path")]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    jobs, disabled, btm = loaded_user_jobs(), disabled_overrides(), btm_records()
    rows = audit_plists(jobs, disabled, btm)
    items = login_items()
    images = mounted_images()
    stale = stale_btm(btm)
    btm_measured = bool(btm)
    if a.json:
        print(json.dumps({"plists": rows, "login_items": items, "mounted_images": images,
                          "stale_btm": stale, "btm_measured": btm_measured}, indent=1, ensure_ascii=False))
        return
    order = {"DEAD": 0, "running": 1, "loaded": 2, "not loaded": 3, "off (user)": 4, "disabled": 5}
    rows.sort(key=lambda r: (order.get(r["verdict"].split(" pid")[0], 6), r["kind"], r["label"]))
    print("## Launch agents and daemons")
    print(f"  {'verdict':<18} {'kind':<13} {'schedule':<24} label  (program)")
    for r in rows:
        note = f"  [{r['note']}]" if r.get("note") else ""
        print(f"  {r['verdict']:<18} {r['kind']:<13} {r.get('schedule', ''):<24} {r['label']}  ({r['program']}{note})")
    print("\n## Login Items (System Settings > General > Login Items)")
    for it in items or [{"name": "none", "path": "", "stale": False}]:
        flag = "  STALE: target missing" if it["stale"] else ""
        print(f"  {it['name']}  {it['path']}{flag}")
    print("\n## Background items registered for apps that no longer exist (System Settings > Login Items)")
    if not btm_measured:
        print("  not measured: `sfltool dumpbtm` did not answer in time")
    for st in stale or ([] if not btm_measured else [{"name": "none", "path": "", "disposition": ""}]):
        print(f"  {st['name']}  {st['path']}  {st['disposition']}")
    print("\n## Mounted disk images (installers people forgot to eject)")
    for i in images or ["none"]:
        print(f"  {i}")


if __name__ == "__main__":
    main()
