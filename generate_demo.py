"""
Generates a realistic fake pButtons HTML file and runs it through the full
parser + analyzer pipeline to produce a demo output report.

Usage:
    ./venv/Scripts/python generate_demo.py
Writes: demo_output.html
"""
import asyncio
import random
import math
from datetime import datetime, timedelta
from pbuttons_parser import parse_sections, build_output
from analyzers import SECTION_ANALYZERS
from analyzers.time_filter import TITLE_TIME_FILTERS
import re

random.seed(42)

# ── Helpers ───────────────────────────────────────────────────────────────────

def ts_range(start: datetime, count: int, step_s: int = 30):
    return [start + timedelta(seconds=i * step_s) for i in range(count)]


def wave(base, amp, n, noise=0.08, period=None):
    """Sine wave + noise. period defaults to n (one full cycle)."""
    p = period or n
    return [
        max(0, base + amp * math.sin(2 * math.pi * i / p)
            + random.gauss(0, base * noise))
        for i in range(n)
    ]


def ramp_spike(base, spike_val, n, spike_start=0.6, spike_width=0.15, noise=0.05):
    out = []
    for i in range(n):
        frac = i / n
        in_spike = spike_start <= frac <= spike_start + spike_width
        v = spike_val if in_spike else base
        out.append(max(0, v + random.gauss(0, v * noise)))
    return out


INTERVALS = 480   # 4 hours × 30s
START = datetime(2026, 6, 15, 0, 5, 0)
TIMES = ts_range(START, INTERVALS, 30)

# ── Section: Configuration ────────────────────────────────────────────────────

CONFIG_PRE = """
Configuration:
  Caché version: IRIS for UNIX (Red Hat Enterprise Linux 8 for x86-64) 2025.1.3 (Build 481_1)
  Instance name: PROD
  Machine: xrdclpdbscol01
  Directory: /iris/sys/
  GUID: A1B2C3D4-E5F6-7890-ABCD-EF1234567890
  License serial: XY-123456
"""

# ── Section: Profile ──────────────────────────────────────────────────────────

PROFILE_PRE = """
Profile run "24hours" started at 00:05 on Jun 15 2026.
Run over 2880 intervals of 30 seconds.
Started by user "admin@example.com".
"""

# ── Section: mgstat ───────────────────────────────────────────────────────────

def make_mgstat():
    glorefs  = wave(45000, 18000, INTERVALS, noise=0.12, period=120)
    gloupds  = wave(8000,  3000,  INTERVALS, noise=0.10, period=120)
    phyrds   = ramp_spike(120, 890, INTERVALS, spike_start=0.55, spike_width=0.12)
    phywrs   = wave(180, 60, INTERVALS, noise=0.08)
    jrnwrts  = wave(320, 80, INTERVALS, noise=0.06)
    wdqsz    = wave(12, 5, INTERVALS, noise=0.15)
    rourefs  = wave(22000, 7000, INTERVALS, noise=0.10, period=90)
    gblsz    = [4096 + random.uniform(-10, 10) for _ in range(INTERVALS)]
    bdfsz    = [2048 + random.uniform(-5, 5)   for _ in range(INTERVALS)]
    bytsnt   = wave(120000, 40000, INTERVALS, noise=0.12)
    bytrcd   = wave(95000,  30000, INTERVALS, noise=0.12)
    rdratio  = [max(0, min(100, r / max(g, 1) * 100))
                for r, g in zip(phyrds, glorefs)]

    lines = ["Date,       Time    , Glorefs, Gloupds,  PhyRds,  PhyWrs, Jrnwrts,   WDQsz, Rourefs, RemGrefs, RemRrefs,  GblSz,  BDBSz,  BytSnt,  BytRcd, Rdratio"]
    for i, t in enumerate(TIMES):
        lines.append(
            f"{t.strftime('%m/%d/%Y')}, {t.strftime('%H:%M:%S')}, "
            f"{glorefs[i]:.0f}, {gloupds[i]:.0f}, {phyrds[i]:.0f}, {phywrs[i]:.0f}, "
            f"{jrnwrts[i]:.0f}, {wdqsz[i]:.1f}, {rourefs[i]:.0f}, "
            f"{random.uniform(50,200):.0f}, {random.uniform(30,150):.0f}, "
            f"{gblsz[i]:.0f}, {bdfsz[i]:.0f}, {bytsnt[i]:.0f}, {bytrcd[i]:.0f}, "
            f"{rdratio[i]:.2f}"
        )
    return "\n".join(lines)


# ── Section: vmstat ───────────────────────────────────────────────────────────

def make_vmstat():
    r    = wave(2.5, 2.0, INTERVALS, noise=0.2, period=80)
    b    = wave(0.3, 0.8, INTERVALS, noise=0.3, period=80)
    swpd = [0] * INTERVALS
    free = wave(55000, 8000, INTERVALS, noise=0.05)
    buff = wave(12000, 1000, INTERVALS, noise=0.03)
    cache= wave(180000,5000, INTERVALS, noise=0.02)
    si   = [0] * INTERVALS
    so   = [0] * INTERVALS
    bi   = wave(400,  200, INTERVALS, noise=0.2)
    bo   = wave(600,  250, INTERVALS, noise=0.2)
    inp  = wave(1200, 300, INTERVALS, noise=0.1)
    cs   = wave(8500, 2000, INTERVALS, noise=0.1)
    us   = wave(28, 8, INTERVALS, noise=0.1)
    sy   = wave(6,  2, INTERVALS, noise=0.1)
    wa   = wave(4,  3, INTERVALS, noise=0.2)
    id_  = [max(0, 100 - us[i] - sy[i] - wa[i]) for i in range(INTERVALS)]
    st   = [0] * INTERVALS

    lines = ["MM/DD/YY HH:MM:SS  r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st"]
    for i, t in enumerate(TIMES):
        lines.append(
            f"{t.strftime('%m/%d/%y')} {t.strftime('%H:%M:%S')} "
            f"{r[i]:.0f} {b[i]:.0f} {swpd[i]:.0f} {free[i]:.0f} {buff[i]:.0f} {cache[i]:.0f} "
            f"{si[i]:.0f} {so[i]:.0f} {bi[i]:.0f} {bo[i]:.0f} {inp[i]:.0f} {cs[i]:.0f} "
            f"{us[i]:.0f} {sy[i]:.0f} {id_[i]:.0f} {wa[i]:.0f} {st[i]:.0f}"
        )
    return "\n".join(lines)


# ── Section: sar -u ───────────────────────────────────────────────────────────

def make_sar_u():
    date_str = START.strftime('%m/%d/%Y')
    lines = [
        f"Linux 5.14.0-427.el9.x86_64 ({date_str})\n",
        f"12:00:01 AM  CPU     %user     %nice   %system   %iowait    %steal     %idle",
    ]
    us  = wave(28, 8,  INTERVALS, noise=0.1)
    sy  = wave(6,  2,  INTERVALS, noise=0.1)
    wa  = wave(4,  3,  INTERVALS, noise=0.2)
    st  = [random.uniform(0, 0.2) for _ in range(INTERVALS)]
    for i, t in enumerate(TIMES):
        idle = max(0, 100 - us[i] - sy[i] - wa[i] - st[i])
        ts = t.strftime('%I:%M:%S %p')
        lines.append(f"{ts}  all  {us[i]:.2f}  0.00  {sy[i]:.2f}  {wa[i]:.2f}  {st[i]:.2f}  {idle:.2f}")
    lines.append(f"Average:  all  {sum(us)/len(us):.2f}  0.00  {sum(sy)/len(sy):.2f}  {sum(wa)/len(wa):.2f}  0.08  62.14")
    return "\n".join(lines)


# ── Section: sar -d ───────────────────────────────────────────────────────────

def make_sar_d():
    date_str = START.strftime('%m/%d/%Y')
    lines = [
        f"Linux 5.14.0-427.el9.x86_64 ({date_str})\n",
        f"12:00:01 AM  DEV   tps  rkB/s  wkB/s  areq-sz  aqu-sz  await  r_await  w_await  svctm  %util",
    ]
    devices = ['sda', 'sdb', 'sdc']
    tps   = {d: wave(120, 60, INTERVALS, noise=0.15) for d in devices}
    rkb   = {d: wave(1200,500,INTERVALS, noise=0.15) for d in devices}
    wkb   = {d: wave(900, 400,INTERVALS, noise=0.15) for d in devices}
    # sda gets a utilisation spike
    util  = {'sda': ramp_spike(35, 88, INTERVALS, spike_start=0.55, spike_width=0.12),
             'sdb': wave(25, 10, INTERVALS, noise=0.1),
             'sdc': wave(18,  8, INTERVALS, noise=0.1)}
    await_= {'sda': ramp_spike(4, 28, INTERVALS, spike_start=0.55, spike_width=0.12),
              'sdb': wave(3.5, 1.2, INTERVALS, noise=0.1),
              'sdc': wave(2.8, 0.8, INTERVALS, noise=0.1)}

    for i, t in enumerate(TIMES):
        ts = t.strftime('%I:%M:%S %p')
        for d in devices:
            u  = min(100, util[d][i])
            aw = await_[d][i]
            lines.append(
                f"{ts}  {d}  {tps[d][i]:.2f}  {rkb[d][i]:.2f}  {wkb[d][i]:.2f}  "
                f"16.38  {random.uniform(0.1,1.2):.2f}  {aw:.2f}  {aw*0.4:.2f}  {aw*0.6:.2f}  "
                f"{aw*0.7:.2f}  {u:.2f}"
            )
    for d in devices:
        avg_u = sum(util[d]) / len(util[d])
        avg_aw = sum(await_[d]) / len(await_[d])
        lines.append(
            f"Average:  {d}  {sum(tps[d])/len(tps[d]):.2f}  "
            f"{sum(rkb[d])/len(rkb[d]):.2f}  {sum(wkb[d])/len(wkb[d]):.2f}  "
            f"16.38  0.42  {avg_aw:.2f}  {avg_aw*0.4:.2f}  {avg_aw*0.6:.2f}  "
            f"{avg_aw*0.7:.2f}  {avg_u:.2f}"
        )
    return "\n".join(lines)


# ── Section: iostat ───────────────────────────────────────────────────────────

def make_iostat():
    lines = [f"Linux 5.14.0-427.el9.x86_64 ({START.strftime('%m/%d/%Y')})"]
    devices = ['sda', 'sdb']
    util   = {'sda': ramp_spike(30, 85, INTERVALS, spike_start=0.55, spike_width=0.12),
               'sdb': wave(20, 8, INTERVALS, noise=0.1)}
    rkb    = {'sda': ramp_spike(1000, 4200, INTERVALS, spike_start=0.55, spike_width=0.12),
               'sdb': wave(600, 200, INTERVALS, noise=0.12)}
    wkb    = {'sda': wave(800, 300, INTERVALS, noise=0.12),
               'sdb': wave(400, 150, INTERVALS, noise=0.1)}
    await_ = {'sda': ramp_spike(3.5, 24, INTERVALS, spike_start=0.55, spike_width=0.12),
               'sdb': wave(2.8,  1.0, INTERVALS, noise=0.1)}
    cpu_us = wave(28, 8,  INTERVALS, noise=0.1)
    cpu_sy = wave(6,  2,  INTERVALS, noise=0.1)
    cpu_wa = wave(4,  3,  INTERVALS, noise=0.2)

    for i, t in enumerate(TIMES):
        ts = t.strftime('%m/%d/%Y %I:%M:%S %p')
        lines.append(f"\n{ts}")
        cpu_idle = max(0, 100 - cpu_us[i] - cpu_sy[i] - cpu_wa[i])
        lines.append(f"avg-cpu:  %user   %nice %system %iowait  %steal   %idle")
        lines.append(f"          {cpu_us[i]:.2f}    0.00   {cpu_sy[i]:.2f}   {cpu_wa[i]:.2f}    0.00   {cpu_idle:.2f}")
        lines.append("")
        lines.append(f"Device  r/s  w/s  rkB/s  wkB/s  rrqm/s  wrqm/s  %rrqm  %wrqm  r_await  w_await  aqu-sz  rareq-sz  wareq-sz  svctm  %util")
        for d in devices:
            u  = min(100, util[d][i])
            aw = await_[d][i]
            r  = rkb[d][i] / 16
            w  = wkb[d][i] / 16
            lines.append(
                f"{d}  {r:.2f}  {w:.2f}  {rkb[d][i]:.2f}  {wkb[d][i]:.2f}  "
                f"0.10  0.25  2.10  4.30  {aw*0.4:.2f}  {aw*0.6:.2f}  "
                f"{random.uniform(0.1,0.8):.2f}  16.38  16.38  {aw*0.7:.2f}  {u:.2f}"
            )
    return "\n".join(lines)


# ── Section: free ─────────────────────────────────────────────────────────────

def make_free():
    lines = ["Date,     Time,      Memtotal,     used,     free,   shared,  buffers,   cached,  adjused,  adjfree,swaptotal, swapused, swapfree,"]
    total = 514823
    for t in TIMES:
        used    = int(random.gauss(121000, 2000))
        free_   = total - used - 244000
        shared  = 4065
        buffers = int(random.gauss(244500, 500))
        cached  = int(random.gauss(384900, 800))
        adjused = used - buffers - cached + shared
        adjfree = total - adjused
        lines.append(
            f"{t.strftime('%m/%d/%y')}, {t.strftime('%H:%M:%S')}, "
            f"   {total},   {used},   {free_},     {shared},   {buffers},   {cached},  "
            f"  {adjused},  {adjfree//1000},   21459,"
        )
    return "\n".join(lines)


# ── Section: sysctl -a ────────────────────────────────────────────────────────

SYSCTL_PRE = """vm.swappiness = 30
vm.dirty_ratio = 40
vm.dirty_background_ratio = 10
vm.overcommit_memory = 0
vm.nr_hugepages = 0
kernel.numa_balancing = 1
kernel.shmmax = 68719476736
kernel.shmall = 4294967296
kernel.sem = 250 32000 100 128
fs.file-max = 65536
net.core.somaxconn = 128
net.ipv4.tcp_max_syn_backlog = 512
kernel.pid_max = 32768
net.ipv4.tcp_keepalive_time = 7200
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
"""

# ── Section: cpu (lscpu) ──────────────────────────────────────────────────────

CPU_PRE = """Architecture:            x86_64
  CPU op-mode(s):        32-bit, 64-bit
  Byte Order:            Little Endian
CPU(s):                  32
  On-line CPU(s) list:   0-31
Vendor ID:               GenuineIntel
  Model name:            Intel(R) Xeon(R) Gold 6226R CPU @ 2.90GHz
    CPU family:          6
    Model:               85
    Stepping:            7
    CPU MHz:             2450.000
    CPU max MHz:         2900.0000
    CPU min MHz:         1000.0000
    BogoMIPS:            5800.00
Virtualization:          VT-x
Caches (sum of all):
  L1d:                   512 KiB (16 instances)
  L1i:                   512 KiB (16 instances)
  L2:                    16 MiB (16 instances)
  L3:                    44 MiB (2 instances)
NUMA:
  NUMA node(s):          2
  NUMA node0 CPU(s):     0-7,16-23
  NUMA node1 CPU(s):     8-15,24-31
Flags:                   fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx pdpe1gb rdtscp lm constant_tsc aes avx avx2 numa
"""

# ── Section: Linux info ───────────────────────────────────────────────────────

LINUXINFO_PRE = """
OS: Red Hat Enterprise Linux release 8.9 (Ootpa)
Kernel: 5.14.0-427.el9.x86_64
Hostname: xrdclpdbscol01
"""

# ── Assemble pButtons HTML ────────────────────────────────────────────────────

def make_section_hr(section_id: str, title: str, pre_content: str) -> str:
    return (
        f'<hr size="4" noshade>\n'
        f'<b><font face="Arial, Helvetica, sans-serif" size="4" color="#0000FF">'
        f'<div id={section_id}></div>{title}</font></b><br>\n'
        f'<pre>{pre_content}</pre>\n'
        f'<p align="right"><font size="1"><a href="#Topofpage">Back to top</a></font></p>\n'
    )


def make_section_p(section_id: str, title: str, pre_content: str) -> str:
    return (
        f'<p> <b><font face="Arial, Helvetica, sans-serif" size="4" color="#0000FF">'
        f'<div id="{section_id}"></div>{title}</font></b></p>\n'
        f'<pre>{pre_content}</pre>\n'
        f'<hr size="4" noshade>\n'
    )


HEADER_HTML = """<html>
<head>
<title>IRIS Performance Data Report. Filename: xrdclpdbscol01_IRIS_20260615_0005_4hours.html</title>
<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">
</head>
<body bgcolor="#FFFFFF" text="#000000"> <!-- Document Version:pButtonsv1.09 Data Version: pButtonsv1.09 -->
<a id="Topofpage"></a>
<table align="center" width="92%" border="1">
<tr><td colspan="9" align="center">
  <font face="Arial,Helvetica,sans-serif" size="4" color="#0000FF"><b>IRIS Performance Data Report</b></font>
</td></tr>
<tr>
  <td align="center"><b><font size="2" color="#0000FF"><a href="#profile">Profile</a></font></b></td>
  <td align="center"><b><font size="2" color="#006600"><a href=#mgstat>mgstat</a></font></b></td>
  <td align="center"><b><font size="2" color="#006600"><a href=#vmstat>vmstat</a></font></b></td>
  <td align="center"><b><font size="2" color="#006600"><a href=#sar-u>sar -u</a></font></b></td>
  <td align="center"><b><font size="2" color="#006600"><a href=#sar-d>sar -d</a></font></b></td>
  <td align="center"><b><font size="2" color="#006600"><a href=#iostat>iostat</a></font></b></td>
  <td align="center"><b><font size="2" color="#006600"><a href=#free>free</a></font></b></td>
  <td align="center"><b><font size="2" color="#006600"><a href=#sysctl-a>sysctl -a</a></font></b></td>
  <td align="center"><b><font size="2" color="#006600"><a href=#cpu>cpu</a></font></b></td>
</tr>
</table>
"""

# Configuration and Profile use the <p> pattern (quoted id)
RAW_HTML = HEADER_HTML
RAW_HTML += make_section_p("Configuration", "Configuration", CONFIG_PRE)
RAW_HTML += make_section_p("Profile", "Profile", PROFILE_PRE)

# All other sections use <hr><b> (unquoted id)
sections_data = [
    ("mgstat",    "mgstat",    make_mgstat()),
    ("vmstat",    "vmstat",    make_vmstat()),
    ("sar-u",     "sar -u",    make_sar_u()),
    ("sar-d",     "sar -d",    make_sar_d()),
    ("iostat",    "iostat",    make_iostat()),
    ("free",      "free",      make_free()),
    ("sysctl-a",  "sysctl -a", SYSCTL_PRE),
    ("Linuxinfo", "Linux info", LINUXINFO_PRE),
    ("cpu",       "cpu",        CPU_PRE),
]

for sec_id, title, content in sections_data:
    RAW_HTML += make_section_hr(sec_id, title, content)

RAW_HTML += "\n</body></html>"


# ── Parse + Analyze + Build ───────────────────────────────────────────────────

async def main():
    print("Parsing sections...")
    header_html, sections = parse_sections(RAW_HTML)
    print(f"  Found {len(sections)} sections: {[s.id for s in sections]}")

    selected_ids = [s.id for s in sections]
    analyzable = [(s, SECTION_ANALYZERS[s.id]) for s in sections if s.id in SECTION_ANALYZERS]
    print(f"  Running {len(analyzable)} analyzers: {[s.id for s, _ in analyzable]}")

    async def run(section, fn):
        import traceback
        try:
            text = '\n'.join(re.findall(r'<pre>(.*?)</pre>', section.content_html, re.DOTALL))
            return section.id, await fn(text)
        except Exception:
            print(f"  [WARN] analyzer {section.id} failed:\n{traceback.format_exc()}")
            return section.id, ''

    results = await asyncio.gather(*[run(s, fn) for s, fn in analyzable])
    analysis = {sid: html for sid, html in results if html}
    print(f"  Analysis produced for: {list(analysis.keys())}")

    print("Building output...")
    output_html = build_output(header_html, sections, selected_ids, analysis=analysis)

    out_path = "demo_output.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output_html)
    print(f"\nDone! Written to {out_path}  ({len(output_html)//1024} kB)")


if __name__ == "__main__":
    asyncio.run(main())
