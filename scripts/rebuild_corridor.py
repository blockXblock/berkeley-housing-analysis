#!/usr/bin/env python3
"""rebuild_corridor.py — one command from a hand-drawn path to finished packages.

WHY THIS EXISTS. Rebuilding a corridor is four steps in a required order, and getting the
order wrong loses work silently: gen_corridor_tour.py writes the tour FROM SCRATCH, so running
it after add_intro_swoop.py removes the swoop without saying so. That hazard is real enough
that the tour file carries a warning about it in its own description. This does the whole chain,
so John can hand over a drawn path and get back something recordable.

  tour (orbits) -> swoop -> cruise (no orbits) -> swoop -> street labels -> .kmz -> packages

  python scripts/rebuild_corridor.py "kml/tours/control_points/Ashby-W-E.kml" \\
      --slug ashby-w2e --name "Ashby Ave W-to-E" --street Ashby \\
      --orbit "3000 SHATTUCK,2955 SHATTUCK"

--orbit targets are matched against building names in geometry.kml. There are NO buildings west
of I-80, so a marina or harbour orbit cannot be expressed this way -- it needs a bare
coordinate, which gen_corridor_tour.py does not yet accept.
"""
import argparse, pathlib, subprocess, sys, zipfile, os

def run(cmd, quiet=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout + r.stderr, file=sys.stderr)
        raise SystemExit(f"failed: {' '.join(cmd[:3])}...")
    if not quiet:
        print(r.stdout.rstrip())
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("control_points")
    ap.add_argument("--slug", required=True, help="output stem, e.g. ashby-w2e")
    ap.add_argument("--name", required=True, help="tour title, without the (no orbits) suffix")
    ap.add_argument("--street", required=True, help="corridor street name, excluded from its own signs")
    ap.add_argument("--orbit", default="", help="comma-separated building-name fragments")
    ap.add_argument("--hold", type=float, default=8.0)
    ap.add_argument("--rise", type=float, default=75.0)
    ap.add_argument("--look-ahead", type=float, default=150.0)
    ap.add_argument("--labels", default=None,
                    help="stem for the street-sign files; defaults to --street lowercased. Label "
                         "files are named per CORRIDOR, not per tour, because the orbit and cruise "
                         "variants of one street share one set of signs.")
    ap.add_argument("--no-swoop", action="store_true")
    a = ap.parse_args()
    cp, py = a.control_points, sys.executable

    for suffix, orbit, title in ((".kml", a.orbit, a.name),
                                 ("-cruise.kml", "", f"{a.name} (no orbits)")):
        out = f"kml/tours/{a.slug}{suffix}" if suffix != ".kml" else f"kml/tours/{a.slug}.kml"
        cmd = [py, "scripts/gen_corridor_tour.py", cp, "--name", title, "--out", out]
        if orbit:
            cmd += ["--orbit", orbit]
        # RUN IT, THEN REPORT. This was `print(run(cmd)... if orbit else f"wrote {out}")`, and a
        # conditional expression only evaluates the branch it takes -- so on the cruise pass the
        # generator was never invoked and the script printed "wrote" over a file it had not
        # written. Every cruise this script claimed to build was actually the previous one, left
        # untouched: bancroft-w2e-cruise was still built from the DERIVED path after John had
        # replaced it.
        stdout = run(cmd)
        print(stdout.strip().splitlines()[-2] if orbit else f"wrote {out}")
        if not pathlib.Path(out).exists():
            raise SystemExit(f"generator reported success but {out} does not exist")
        if not a.no_swoop:
            run([py, "scripts/add_intro_swoop.py", out, "--out", out,
                 "--hold", str(a.hold), "--rise", str(a.rise), "--look-ahead", str(a.look_ahead)])

    stem = a.labels or a.street.lower().replace(" ", "-")
    lab = f"kml/tours/labels/{stem}-street-labels.kml"
    print(run([py, "scripts/gen_street_labels.py", cp, "--name", a.street,
               "--out", lab, "--scale", "2.5", "--alt", "20"]).splitlines()[1].strip())
    with zipfile.ZipFile(lab[:-4] + ".kmz", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("doc.kml", open(lab, encoding="utf-8").read())
        z.write("kml/tours/labels/transparent-1x1.png", "transparent-1x1.png")

    print(run([py, "scripts/build_tour_package.py", "--all"]).strip().splitlines()[-1])
    print(f"\nrecord: kml/tours/packages/{a.slug}__geom-<sha>.kmz  +  kml/tours/labels/{stem}-street-labels.kmz")


if __name__ == "__main__":
    main()
