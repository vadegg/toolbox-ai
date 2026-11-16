#!/usr/bin/env python3
"""Processes grouped by application, plus the things worth a second look.

Read-only. Usage: procs.py [--top N] [--live] [--json]

  --top N   rows per table (default 30)
  --live    sample real CPU use with `top -l 2` (adds ~3 s). The %cpu column
            from `ps` is a lifetime average, which hides a process that started
            spinning an hour ago.
  --json    machine-readable output instead of tables

Memory is summed as RSS per application bundle. RSS double-counts shared
libraries, so treat the figure as a ranking, not an invoice.
"""
import argparse
import collections
import json
import os
import re
import subprocess
import sys

DEV = re.compile(
    r"(^|/| )(node|npm|npx|pnpm|yarn|bun|deno|python[0-9.]*|uv|uvicorn|gunicorn|flask|"
    r"vite|next|webpack|esbuild|tsc|ts-node|cargo|java|ruby|rails|php|postgres|"
    r"redis-server|mongod|mysqld|jupyter|streamlit)( |$)"
)
VM = re.compile(
    r"(Virtualization\.VirtualMachine|qemu-system|limactl|com\.docker\.|Docker Desktop|"
    r"prl_vm_app|vmware-vmx|UTM\.app|VirtualBoxVM|OrbStack|multipassd|podman)",
    re.I,
)
SYSTEM_HOGS = {
    "mediaanalysisd", "photoanalysisd", "WindowServer", "mds", "mds_stores",
    "mdworker_shared", "corespotlightd", "kernel_task", "bird", "cloudd",
    "fileproviderd", "backupd", "softwareupdated", "nsurlsessiond", "sharingd",
    "coreduetd", "suggestd", "spotlightknowledged", "photolibraryd", "syspolicyd",
}


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def etime_seconds(s):
    days = 0
    if "-" in s:
        d, s = s.split("-", 1)
        days = int(d)
    parts = [int(p) for p in s.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, sec = parts
    return days * 86400 + h * 3600 + m * 60 + sec


def app_name(comm):
    m = re.search(r"/([^/]+)\.app/", comm)
    if m:
        return m.group(1)
    if comm.startswith("/"):
        return comm.rsplit("/", 1)[-1]
    m = re.match(r"^(.*?)(?: Helper| \(| Service)", comm)
    return m.group(1) if m else comm


def processes():
    rows = []
    me = os.environ.get("USER") or os.getlogin()
    args_by_pid = {}
    for line in run(["ps", "-axo", "pid=,args="]).splitlines():
        line = line.strip()
        if not line:
            continue
        pid, _, args = line.partition(" ")
        args_by_pid[int(pid)] = args.strip()
    for line in run(["ps", "-axo", "pid=,ppid=,user=,%cpu=,%mem=,rss=,etime=,time=,comm="]).splitlines():
        parts = line.strip().split(None, 8)
        if len(parts) < 9:
            continue
        pid, ppid, user, cpu, mem, rss, etime, cputime, comm = parts
        rows.append({
            "pid": int(pid), "ppid": int(ppid), "user": user, "cpu": float(cpu),
            "mem": float(mem), "rss_kb": int(rss), "etime": etime,
            "etime_s": etime_seconds(etime), "cputime": cputime, "comm": comm,
            "args": args_by_pid.get(int(pid), comm), "mine": user == me,
        })
    return rows


def launchd_pids():
    pids = set()
    for line in run(["launchctl", "list"]).splitlines()[1:]:
        pid = line.split("\t")[0]
        if pid.isdigit():
            pids.add(int(pid))
    return pids


def live_cpu(top_n):
    out = run(["top", "-l", "2", "-n", str(top_n), "-o", "cpu", "-stats", "pid,cpu,command"])
    samples = out.split("Processes:")
    if len(samples) < 3:
        return []
    rows = []
    for line in samples[-1].splitlines():
        m = re.match(r"^\s*(\d+)\s+([\d.]+)\s+(.+?)\s*$", line)
        if m:
            rows.append({"pid": int(m.group(1)), "cpu": float(m.group(2)), "command": m.group(3)})
    return rows


def fmt_gb(kb):
    return f"{kb / 1048576:.2f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    rows = processes()
    jobs = launchd_pids()
    groups = collections.defaultdict(lambda: {"rss_kb": 0, "cpu": 0.0, "procs": 0, "longest_etime": "", "longest_s": -1})
    for r in rows:
        g = groups[app_name(r["comm"])]
        g["rss_kb"] += r["rss_kb"]
        g["cpu"] += r["cpu"]
        g["procs"] += 1
        if r["etime_s"] > g["longest_s"]:
            g["longest_s"], g["longest_etime"] = r["etime_s"], r["etime"]
    by_app = sorted(groups.items(), key=lambda kv: -kv[1]["rss_kb"])[: a.top]

    orphans = [r for r in rows if r["mine"] and r["ppid"] == 1 and r["pid"] not in jobs
               and DEV.search(r["args"]) and r["etime_s"] >= 3600
               and "/Applications/" not in r["comm"] and ".app/" not in r["comm"]]
    vms = [r for r in rows if VM.search(r["args"])]
    hogs = [r for r in rows if r["comm"].rsplit("/", 1)[-1] in SYSTEM_HOGS
            and (r["cpu"] >= 5 or etime_seconds(r["cputime"].split(".")[0]) >= 600)]
    noise = {"distnoted", "cfprefsd", "zsh", "bash", "sh", "login", "mdworker_shared", "trustd", "launchd"}
    helpers = [(name, g["procs"]) for name, g in groups.items() if g["procs"] >= 10 and name not in noise]
    helpers.sort(key=lambda x: -x[1])
    live = live_cpu(a.top) if a.live else []

    if a.json:
        print(json.dumps({
            "by_app": [{"app": n, **g} for n, g in by_app],
            "orphans": orphans, "vms": vms, "system_hogs": hogs,
            "helper_counts": helpers, "live_cpu": live,
            "total_processes": len(rows), "mine": sum(r["mine"] for r in rows),
        }, indent=1, ensure_ascii=False))
        return

    print(f"Processes: {len(rows)} total, {sum(r['mine'] for r in rows)} owned by this user\n")
    print("## Memory by application (RSS sum, GiB) | CPU% (ps average) | processes | longest running")
    for name, g in by_app:
        print(f"  {fmt_gb(g['rss_kb']):>7}  {g['cpu']:6.1f}  {g['procs']:4d}  {g['longest_etime']:>14}  {name}")

    if live:
        print("\n## Real CPU use right now (second `top` sample)")
        for r in live[:15]:
            print(f"  {r['cpu']:6.1f}%  pid {r['pid']:<6} {r['command']}")

    print("\n## Likely orphaned dev processes (parent is launchd, not a launchd job, older than 1 h)")
    if not orphans:
        print("  none")
    for r in orphans:
        print(f"  pid {r['pid']:<6} up {r['etime']:>12}  rss {fmt_gb(r['rss_kb'])} GiB  {r['args'][:110]}")

    print("\n## Virtual machines and container engines")
    if not vms:
        print("  none running")
    for r in vms:
        print(f"  pid {r['pid']:<6} up {r['etime']:>12}  rss {fmt_gb(r['rss_kb'])} GiB  {r['args'][:110]}")

    print("\n## System daemons worth a look (CPU >= 5% or >= 10 min of CPU time)")
    if not hogs:
        print("  none")
    for r in hogs:
        print(f"  {r['comm'].rsplit('/', 1)[-1]:<22} cpu {r['cpu']:5.1f}%  cpu time {r['cputime']:>10}  up {r['etime']:>12}  rss {fmt_gb(r['rss_kb'])} GiB")

    print("\n## Applications with many helper processes")
    for name, n in helpers[:10]:
        print(f"  {n:4d}  {name}")


if __name__ == "__main__":
    main()
