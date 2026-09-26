#!/usr/bin/env python3
"""migrate_video_facades.py — replace the nine autoplaying iframes with click-to-play posters.

THE COST BEING REMOVED. Nine YouTube players, every one autoplay=1&loop=1, none lazy, all
booting before anyone scrolls. Measured on the homepage: DOM ready at 835 ms, load event at
8,111 ms -- a 7.3 second tail that is entirely the players -- on a page 63,402 px long, so
eight of the nine were looping video far below the fold for a reader who never saw them.

WHY <noscript> AND NOT DELETION. Two scripts identify a video block by the literal string
'youtube.com/embed' -- update_legend.py (which writes the colour legend into every video
paragraph) and publish_video.py (which finds, retitles and replaces blocks). Deleting the
iframe would silently break both: new flyovers would publish with no legend. Keeping the
canonical iframe inside <noscript> preserves that contract exactly, costs nothing when JS is
on (the browser does not fetch inside noscript), and gives no-JS readers a working video --
so the fallback is real, not a trick to satisfy a grep.

PRIVACY. Nothing reaches Google until a reader clicks: the poster is one lazily-loaded image,
and the player is youtube-nocookie.com, injected on click.
"""
import re, sys, pathlib

PAGE = pathlib.Path("docs/index.html")
IFRAME = re.compile(
    r'<div style="border-radius: 8px; overflow: hidden; position: relative;'
    r' padding-bottom: 56\.25%; height: 0;">\s*'
    r'(<iframe\b.*?</iframe>)\s*</div>', re.S)


def facade(m):
    iframe = m.group(1)
    vid = re.search(r'embed/([A-Za-z0-9_-]{11})', iframe).group(1)
    title = re.search(r'title="([^"]*)"', iframe)
    title = title.group(1) if title else "Berkeley housing flyover"
    # the fallback player: same video, no autoplay, no third-party cookies
    fallback = re.sub(r'src="[^"]*"',
                      f'src="https://www.youtube.com/embed/{vid}?rel=0&amp;modestbranding=1"',
                      iframe)
    return (
        '<div class="vfacade" data-yt="' + vid + '">\n'
        '    <button type="button" class="vfacade-btn" aria-label="Play video: ' + title + '">\n'
        '      <img src="https://i.ytimg.com/vi/' + vid + '/maxresdefault.jpg" alt=""\n'
        '           loading="lazy" decoding="async" width="1280" height="720">\n'
        '      <span class="vfacade-play" aria-hidden="true"></span>\n'
        '    </button>\n'
        '    <noscript>' + fallback + '</noscript>\n'
        '  </div>')


CSS = """
    /* Click-to-play video posters. The iframe is injected on click (see the script at the
       end of the body); until then a flyover costs one lazily-loaded image, not a player. */
    .vfacade { position: relative; padding-bottom: 56.25%; height: 0; border-radius: 8px;
               overflow: hidden; background: #1a365d; }
    .vfacade > iframe, .vfacade noscript iframe {
               position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0; }
    .vfacade-btn { position: absolute; inset: 0; width: 100%; height: 100%; padding: 0;
               border: 0; background: none; cursor: pointer; display: block; }
    .vfacade-btn img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .vfacade-play { position: absolute; left: 50%; top: 50%; width: 68px; height: 48px;
               margin: -24px 0 0 -34px; border-radius: 12px; background: rgba(26,54,93,.85);
               transition: background .15s, transform .15s; }
    .vfacade-play::after { content: ""; position: absolute; left: 27px; top: 14px;
               border-style: solid; border-width: 10px 0 10px 16px;
               border-color: transparent transparent transparent #fff; }
    .vfacade-btn:hover .vfacade-play,
    .vfacade-btn:focus-visible .vfacade-play { background: #c4302b; transform: scale(1.08); }
    .vfacade-btn:focus-visible { outline: 3px solid #3182ce; outline-offset: 3px; }
"""

JS = """<script>
/* Swap a poster for the real player on click. Nothing contacts YouTube before that:
   youtube-nocookie, and autoplay only because the reader just asked for it. */
document.addEventListener('click', function (e) {
  var btn = e.target.closest && e.target.closest('.vfacade-btn');
  if (!btn) return;
  var box = btn.parentNode, id = box.getAttribute('data-yt');
  if (!id) return;
  var f = document.createElement('iframe');
  f.src = 'https://www.youtube-nocookie.com/embed/' + id +
          '?autoplay=1&rel=0&modestbranding=1&controls=1';
  f.title = btn.getAttribute('aria-label').replace(/^Play video: /, '');
  f.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
  f.allowFullscreen = true;
  box.textContent = '';
  box.appendChild(f);
  f.focus();
});
</script>
"""


def main():
    h = PAGE.read_text(encoding="utf-8")
    before = len(IFRAME.findall(h))
    if before == 0:
        sys.exit("No autoplay iframe blocks matched — already migrated, or the markup moved.")
    h = IFRAME.sub(facade, h)
    if ".vfacade {" not in h:
        h = h.replace("    </style>", CSS + "    </style>", 1)
    if "vfacade-btn" not in h.split("</body>")[-2][-2000:] and "closest('.vfacade-btn')" not in h:
        h = h.replace("</body>", JS + "</body>", 1)
    PAGE.write_text(h, encoding="utf-8")
    print(f"replaced {before} autoplaying iframe(s) with click-to-play posters")


if __name__ == "__main__":
    main()
