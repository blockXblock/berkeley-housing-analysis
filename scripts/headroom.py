#!/usr/bin/env python3
"""headroom.py — is this machine fit to record a Google Earth tour right now?

WHY THIS EXISTS. Recording a 7-minute 1080p tour out of Google Earth Pro on an 8 GB Mac is the
most memory-hungry thing this project does, and when the machine is short the failure does not
look like a memory failure. It looks like a render that stalls, or Movie Maker that will not
start, or Earth wedged with unresponsive menus. Five sessions were spent diagnosing those symptoms
one at a time before notes/2026-09-04_8gb_memory_playbook_ge_tours.md tied them together. This
turns that playbook into one command with a verdict.

THE THRESHOLD THAT IS NOT OBVIOUS. Watch swap TOTAL, not swap used. macOS grows and SHRINKS the
swapfiles with free boot-disk space, and on 2026-09-05 the ceiling fell 7.0 -> 4.1 -> 3.1 GB in a
morning as the disk filled. The ratio IMPROVES while that happens: "2.9 of 4.1 used" reads
healthier than "6.2 of 7.0" and is materially worse, because the headroom was taken away rather
than consumed. A check that watches the percentage would have called that morning fine, and Movie
Maker could not allocate a 1080p encoder.

  python3 scripts/headroom.py            # verdict + the numbers
  python3 scripts/headroom.py --json     # same, machine-readable
  python3 scripts/headroom.py --history  # how swap ceiling and disk have moved across runs

Exit status: 0 = safe to record, 1 = fix something first. So it can gate a script.
"""
import argparse, json, os, re, shutil, subprocess, sys, time

HIST = os.path.expanduser("~/berkeley-data/scratch/headroom_history.jsonl")

# Thresholds, each with the incident that set it.
DISK_MIN_GB = 20.0      # playbook hazard box: below this macOS cannot grow swap
SWAP_USED_MAX = 0.85    # playbook §3.8: >85% used -> reboot before recording
# macOS DELIBERATELY keeps "pages free" near zero -- spare RAM is used as cache, so a low free
# figure is normal and is NOT evidence of trouble on its own. The first version of this script
# blocked on it and would have refused a healthy machine. memory_pressure's system-wide free
# percentage is the number that actually tracks the crises: 37% on the morning Movie Maker could
# not start, against the Aug 26 wedge at single digits.
PRESSURE_MIN_PCT = 20.0
UPTIME_MAX_DAYS = 3.0   # only a reboot empties swap; Aug 30 failed after 4 days
SWAP_TOTAL_MIN_GB = 4.0 # below this a 1080p encoder has nowhere to go (Sep 5)


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


def read():
    d = {"at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    m = re.search(r"total = ([\d.]+)M.*used = ([\d.]+)M", sh("sysctl -n vm.swapusage"))
    d["swap_total_gb"] = float(m.group(1)) / 1024 if m else 0.0
    d["swap_used_gb"] = float(m.group(2)) / 1024 if m else 0.0
    d["swap_used_frac"] = d["swap_used_gb"] / d["swap_total_gb"] if d["swap_total_gb"] else 0.0

    vm = sh("vm_stat")
    ps = int(re.search(r"page size of (\d+)", vm).group(1))
    def pages(label):
        mm = re.search(rf"{label}:\s+(\d+)", vm)
        return int(mm.group(1)) * ps / 1024**3 if mm else 0.0
    d["free_ram_gb"] = pages("Pages free")          # informational only -- see PRESSURE_MIN_PCT
    mp = re.search(r"free percentage:\s*(\d+)", sh("memory_pressure"))
    d["pressure_free_pct"] = float(mp.group(1)) if mp else None
    d["compressed_gb"] = pages("Pages occupied by compressor")
    d["ram_total_gb"] = int(sh("sysctl -n hw.memsize")) / 1024**3

    du = shutil.disk_usage("/")
    d["disk_free_gb"] = du.free / 1024**3
    boot = float(re.search(r"sec = (\d+)", sh("sysctl -n kern.boottime")).group(1))
    d["boot_epoch"] = boot
    d["uptime_days"] = (time.time() - boot) / 86400
    d["load_1m"] = float(sh("sysctl -n vm.loadavg").split()[1])
    return d


def verdict(d, prev):
    """Returns (ok, [problems], [notes]). A problem blocks recording; a note is worth knowing."""
    bad, note = [], []
    if d["disk_free_gb"] < DISK_MIN_GB:
        bad.append(f"boot disk {d['disk_free_gb']:.1f} GB free, want >= {DISK_MIN_GB:.0f} — "
                   "this is what caps the swap ceiling")
    # ZERO SWAP IS THE BEST STATE, NOT THE WORST. After a reboot macOS has created no swapfile at
    # all -- /private/var/vm holds only sleepimage -- and vm.swapusage reports 0.00M total. The
    # first version read that as a collapsed ceiling and told John to reboot a machine he had just
    # rebooted twice. A ceiling only means anything once one exists.
    if d["swap_total_gb"] == 0:
        note.append("no swapfile yet — macOS has not needed one since boot, which is the "
                    "healthiest state there is")
    elif d["swap_total_gb"] < SWAP_TOTAL_MIN_GB:
        bad.append(f"swap CEILING only {d['swap_total_gb']:.1f} GB — too small for a 1080p "
                   "encoder; free boot disk, then reboot")
    if d["swap_used_frac"] > SWAP_USED_MAX:
        bad.append(f"swap {d['swap_used_frac']*100:.0f}% used — only a reboot empties it")
    if d["pressure_free_pct"] is not None and d["pressure_free_pct"] < PRESSURE_MIN_PCT:
        bad.append(f"memory pressure: only {d['pressure_free_pct']:.0f}% free system-wide — "
                   "Movie Maker will fail to allocate an encoder")
    if d["uptime_days"] > UPTIME_MAX_DAYS:
        note.append(f"up {d['uptime_days']:.1f} days — swap does not clear without a reboot")
    # A high load in the first ten minutes after boot is Spotlight, Time Machine and the neural
    # engine settling, not a problem. Measured 2026-09-05: 124.9 at one minute, 18.6 at four.
    if d["load_1m"] > 8:
        if d["uptime_days"] * 1440 < 10:
            note.append(f"load average {d['load_1m']:.1f}, but only "
                        f"{d['uptime_days']*1440:.0f} min since boot — post-boot settling "
                        "(Spotlight, Time Machine, neural engine); give it a few minutes")
        else:
            note.append(f"load average {d['load_1m']:.1f} — something is already working hard")
    # Compare ceilings only WITHIN one boot. Across a restart the ceiling legitimately drops to
    # zero, which is the reboot working, not the disk squeezing it.
    same_boot = prev and prev.get("boot_epoch") == d["boot_epoch"]
    if same_boot and d["swap_total_gb"] > 0 and d["swap_total_gb"] < prev.get("swap_total_gb", 0) - 0.4:
        bad.append(f"swap ceiling SHRANK {prev['swap_total_gb']:.1f} -> {d['swap_total_gb']:.1f} GB "
                   "since the last check — the disk is squeezing it")
    return (not bad), bad, note


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--history", action="store_true")
    a = ap.parse_args()

    if a.history:
        if not os.path.exists(HIST):
            raise SystemExit("no history yet")
        print(f"  {'when':17} {'swap ceiling':>13} {'used':>8} {'disk free':>11} {'free RAM':>9}")
        for line in open(HIST):
            h = json.loads(line)
            print(f"  {h['at'][:16]:17} {h['swap_total_gb']:10.1f} GB {h['swap_used_gb']:6.1f} GB "
                  f"{h['disk_free_gb']:8.1f} GB {h['free_ram_gb']:6.2f} GB")
        return

    d = read()
    prev = None
    if os.path.exists(HIST):
        lines = [l for l in open(HIST) if l.strip()]
        if lines:
            prev = json.loads(lines[-1])
    ok, bad, note = verdict(d, prev)
    d["ok"] = ok

    os.makedirs(os.path.dirname(HIST), exist_ok=True)
    with open(HIST, "a") as f:
        f.write(json.dumps(d) + "\n")

    if a.json:
        print(json.dumps(d, indent=2))
        sys.exit(0 if ok else 1)

    pf = f"{d['pressure_free_pct']:.0f}%" if d["pressure_free_pct"] is not None else "?"
    print(f"  RAM {d['ram_total_gb']:.0f} GB  ·  {pf} free system-wide  ·  "
          f"compressed {d['compressed_gb']:.1f} GB  (pages-free {d['free_ram_gb']:.2f} GB, "
          "normally near zero on macOS)")
    print(f"  swap {d['swap_used_gb']:.1f} of {d['swap_total_gb']:.1f} GB ceiling "
          f"({d['swap_used_frac']*100:.0f}% used)"
          + (f"   [was {prev['swap_total_gb']:.1f} GB ceiling]" if prev else ""))
    print(f"  boot disk {d['disk_free_gb']:.1f} GB free  ·  up {d['uptime_days']:.1f} days  ·  "
          f"load {d['load_1m']:.1f}")
    print()
    for b in bad:
        print(f"  ✗ {b}")
    for n in note:
        print(f"  · {n}")
    print()
    # SAY WHAT TO DO, NOT JUST WHETHER. The first wording was a bare GO / NO, and "NO" reads as
    # ambiguous the moment a reboot is the remedy -- no what? John asked exactly that. The verdict
    # is an answer to "can I record right now", and when it is no the next action must be spelled
    # out in the same breath.
    if ok:
        print("  READY TO RECORD.")
        print("  Earth + one terminal, load ONE tour package, record immediately.")
    else:
        print("  NOT READY TO RECORD — reboot before trying.")
        print("  Why a reboot: only a restart empties swap, and the swap ceiling will not")
        print("  recover while the machine is up. Before restarting:")
        print("    1. quit Chrome and any other browser")
        print("    2. quit Google Earth gracefully — `kill <pid>`, never `kill -9`,")
        print("       or Movie Maker loses its resolution and output-path settings")
        if d["disk_free_gb"] < DISK_MIN_GB:
            print(f"    3. free {DISK_MIN_GB - d['disk_free_gb']:.1f} GB more on the boot disk "
                  "— this is what caps the swap ceiling")
        print("    then reboot, and run this again.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
