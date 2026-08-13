"""Build drawing.html - a self-contained drafting sheet for the cradle.

Renders every view out of stand.scad in both a light and a dark ground, then
inlines them into page.tpl.html as base64 data URIs. Self-contained is a hard
requirement: the page is published as an Artifact, whose CSP blocks requests to
any external host, so nothing may be loaded by URL.

    python build_page.py            # reuse views/ if already rendered
    python build_page.py --render   # re-render every view first (~3 min)
"""
import base64
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
SCAD = HERE / "stand.scad"
TPL = HERE / "page.tpl.html"
OUT = HERE / "drawing.html"
VIEWS = HERE / "views"

OPENSCAD = r"E:\dev\openscad\openscad-2021.01\openscad.exe"

# name -> (camera, extra args). Camera is OpenSCAD's gimbal form:
# translate x,y,z then rotate x,y,z then distance (0 = fit via --viewall).
CAMERAS = {
    "iso":   ("0,0,0,65,0,200,0", []),
    "front": ("0,0,0,90,0,180,0", []),
    "side":  ("0,0,0,90,0,270,0", []),
    "top":   ("0,0,0,0,0,180,0",  []),
    "fit":   ("0,0,0,72,0,205,0", ["-D", "show_pebble=true"]),
}

# Cornfield is OpenSCAD's default pale ground; Tomorrow Night is the darkest
# that still separates the cut faces from the body.
SCHEMES = {"light": "Cornfield", "dark": "Tomorrow Night"}


def render_views():
    VIEWS.mkdir(exist_ok=True)
    for name, (camera, extra) in CAMERAS.items():
        for theme, scheme in SCHEMES.items():
            target = VIEWS / f"{name}-{theme}.png"
            print(f"  rendering {target.name} ...", flush=True)
            subprocess.run(
                [OPENSCAD, "--render", "-o", str(target),
                 f"--colorscheme={scheme}", "--viewall", "--autocenter",
                 f"--camera={camera}", "--imgsize=600,600",
                 *extra, str(SCAD)],
                check=True, capture_output=True,
            )


def uri(name):
    return "data:image/png;base64," + base64.b64encode(
        (VIEWS / name).read_bytes()).decode("ascii")


def main():
    if "--render" in sys.argv or not VIEWS.is_dir():
        render_views()

    html = TPL.read_text(encoding="utf-8")
    for name in CAMERAS:
        for theme in SCHEMES:
            html = html.replace(f"{{{{{name.upper()}_{theme.upper()}}}}}",
                                uri(f"{name}-{theme}.png"))

    missing = sorted(set(re.findall(r"\{\{[A-Z_]+\}\}", html)))
    if missing:
        raise SystemExit(f"unsubstituted placeholders: {missing}")

    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT}  ({len(html) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
