#!/usr/bin/env python3
"""
build_posts.py - turn Word documents into blog posts for In Transit.

WHAT IT DOES
------------
Reads every .docx file in the drop folder, and for each one:
  1. Reads the info block at the top (Title, Date, Author, Tag, Excerpt).
  2. Converts the body into HTML (paragraphs, headings, quotes, lists,
     bold/italic, links).
  3. Pulls out any photos embedded in the document and saves them into
     blog/images/.
  4. Writes a finished post page into blog/.
  5. Rebuilds the post list on the blog page and the three most recent
     posts on the home page.

It is safe to run over and over. Each run regenerates everything from the
Word documents, so the documents are always the source of truth.

HOW TO RUN IT
-------------
Open Terminal and run:

    python3 tools/build_posts.py

Then commit and push in GitHub Desktop to publish.

No installation needed - this uses only what comes with Python.
"""

import html
import os
import re
import shutil
import sys
import zipfile
from datetime import datetime
from xml.etree import ElementTree as ET

# ---------------------------------------------------------------------------
# SETTINGS - change these if you move things around
# ---------------------------------------------------------------------------

# Where Liz's Word documents live (iCloud Drive, synced to this Mac).
DROP_FOLDER = os.path.expanduser(
    "~/Library/Mobile Documents/com~apple~CloudDocs/Blog Posts"
)

# The site itself. Defaults to the folder this script lives in, one level up.
SITE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOG_DIR = os.path.join(SITE_ROOT, "blog")
IMAGES_DIR = os.path.join(BLOG_DIR, "images")

AUTHORS = ["Stephen Bosch", "Liz Barranco"]

# XML namespaces used inside a .docx file
NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}


# ---------------------------------------------------------------------------
# READING A .DOCX
# ---------------------------------------------------------------------------

def load_docx(path):
    """Open the .docx (which is really a zip) and return its parts."""
    z = zipfile.ZipFile(path)
    document = ET.fromstring(z.read("word/document.xml"))

    # Map relationship ids -> targets, so we can resolve images and links.
    rels = {}
    try:
        rel_root = ET.fromstring(z.read("word/_rels/document.xml.rels"))
        for rel in rel_root:
            rels[rel.get("Id")] = rel.get("Target")
    except KeyError:
        pass

    return z, document, rels


def run_text(run):
    """Get the text out of a single run, with bold/italic applied."""
    parts = []
    for t in run.iter():
        tag = t.tag.split("}")[-1]
        if tag == "t":
            parts.append(html.escape(t.text or ""))
        elif tag == "tab":
            parts.append(" ")
        elif tag == "br":
            parts.append("<br />")
    text = "".join(parts)
    if not text.strip():
        return text

    props = run.find("w:rPr", NS)
    if props is not None:
        # A w:b / w:i element means on, unless it explicitly says val="0"
        bold = props.find("w:b", NS)
        italic = props.find("w:i", NS)
        if bold is not None and bold.get(
            "{%s}val" % NS["w"], "1"
        ) not in ("0", "false"):
            text = "<strong>%s</strong>" % text
        if italic is not None and italic.get(
            "{%s}val" % NS["w"], "1"
        ) not in ("0", "false"):
            text = "<em>%s</em>" % text
    return text


def paragraph_images(para, rels, z, slug, counter):
    """Find images in a paragraph, save them, return <img> tags."""
    tags = []
    for blip in para.iter("{%s}blip" % NS["a"]):
        rid = blip.get("{%s}embed" % NS["r"])
        target = rels.get(rid)
        if not target:
            continue
        source = "word/" + target.replace("../", "")
        try:
            data = z.read(source)
        except KeyError:
            continue

        counter[0] += 1
        ext = os.path.splitext(target)[1].lower() or ".jpg"
        if ext == ".jpeg":
            ext = ".jpg"
        name = "%s-%d%s" % (slug, counter[0], ext)

        os.makedirs(IMAGES_DIR, exist_ok=True)
        with open(os.path.join(IMAGES_DIR, name), "wb") as f:
            f.write(data)

        tags.append('<img src="images/%s" alt="" />' % name)
    return tags


def paragraph_html(para, rels, z, slug, counter):
    """Convert one Word paragraph into HTML. Returns (kind, html)."""
    # Images first - a paragraph holding a photo usually has no text.
    imgs = paragraph_images(para, rels, z, slug, counter)

    pieces = []
    for child in para:
        tag = child.tag.split("}")[-1]
        if tag == "r":
            pieces.append(run_text(child))
        elif tag == "hyperlink":
            rid = child.get("{%s}id" % NS["r"])
            href = rels.get(rid, "#")
            inner = "".join(run_text(rr) for rr in child.findall("w:r", NS))
            if inner.strip():
                pieces.append(
                    '<a href="%s">%s</a>' % (html.escape(href), inner)
                )

    text = "".join(pieces).strip()

    if imgs and not text:
        return ("image", "\n      ".join(imgs))
    if not text:
        return (None, "")

    # What kind of paragraph is it? Word tells us via its style name.
    style = ""
    ppr = para.find("w:pPr", NS)
    if ppr is not None:
        st = ppr.find("w:pStyle", NS)
        if st is not None:
            style = (st.get("{%s}val" % NS["w"]) or "").lower()
        is_list = ppr.find("w:numPr", NS) is not None
    else:
        is_list = False

    if style.startswith("heading"):
        return ("h2", "<h2>%s</h2>" % text)
    if "quote" in style:
        return ("quote", "<blockquote>\n        %s\n      </blockquote>" % text)
    if is_list or style == "listparagraph":
        return ("li", "<li>%s</li>" % text)

    out = "<p>%s</p>" % text
    if imgs:
        out += "\n      " + "\n      ".join(imgs)
    return ("p", out)


# ---------------------------------------------------------------------------
# PARSING THE POST
# ---------------------------------------------------------------------------

FIELDS = ("title", "date", "author", "tag", "excerpt")


def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "post"


def parse_date(value):
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d %B %Y", "%B %d, %Y", "%d %b %Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(
        "Could not understand the date '%s'. Use YYYY-MM-DD, "
        "for example 2026-07-13." % value
    )


def parse_post(path):
    """Read one .docx and return everything needed to build a post page."""
    z, document, rels = load_docx(path)
    body = document.find("w:body", NS)
    paragraphs = body.findall("w:p", NS)

    meta = {}
    first_body_index = 0

    # The info block: "Title: ..." lines at the top of the document.
    for i, para in enumerate(paragraphs):
        text = "".join(
            "".join(t.text or "" for t in r.iter("{%s}t" % NS["w"]))
            for r in para.findall("w:r", NS)
        ).strip()

        if not text:
            if meta:
                first_body_index = i + 1
                break
            continue

        match = re.match(r"^\s*(\w+)\s*:\s*(.*)$", text)
        if match and match.group(1).lower() in FIELDS:
            meta[match.group(1).lower()] = match.group(2).strip()
            first_body_index = i + 1
        else:
            first_body_index = i
            break

    missing = [f for f in ("title", "date", "author") if not meta.get(f)]
    if missing:
        raise ValueError(
            "%s is missing required field(s): %s.\nAdd lines like "
            "'Title: My post' at the very top of the document."
            % (os.path.basename(path), ", ".join(missing))
        )

    date = parse_date(meta["date"])
    slug = slugify(meta["title"])

    author = meta["author"].strip()
    for known in AUTHORS:
        if author.lower() in known.lower():
            author = known
            break

    # Convert the body
    counter = [0]
    blocks = []
    for para in paragraphs[first_body_index:]:
        kind, out = paragraph_html(para, rels, z, slug, counter)
        if out:
            blocks.append((kind, out))
    z.close()

    # Group consecutive list items into a single <ul>
    content = []
    i = 0
    while i < len(blocks):
        kind, out = blocks[i]
        if kind == "li":
            items = []
            while i < len(blocks) and blocks[i][0] == "li":
                items.append("  " + blocks[i][1])
                i += 1
            content.append("<ul>\n      %s\n      </ul>" % "\n      ".join(items))
            continue
        content.append(out)
        i += 1

    return {
        "title": meta["title"],
        "date": date,
        "author": author,
        "tag": meta.get("tag", "").strip(),
        "excerpt": meta.get("excerpt", "").strip(),
        "slug": slug,
        "content": "\n\n      ".join(content),
        "images": counter[0],
        "source": os.path.basename(path),
    }


# ---------------------------------------------------------------------------
# WRITING THE POST PAGE
# ---------------------------------------------------------------------------

POST_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title_esc} | In Transit</title>
  <meta name="description" content="{excerpt_attr}" />
  <link rel="stylesheet" href="../style.css" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet" />
  <style>
    .post-body {{ max-width: 680px; margin-inline: auto; padding: 4rem 1.5rem 6rem; }}
    .post-back {{ display: inline-block; font-size: 0.85rem; color: var(--color-text-muted); margin-bottom: 2rem; transition: color 150ms ease; }}
    .post-back:hover {{ color: var(--color-accent); }}
    .post-header {{ margin-bottom: 3rem; padding-bottom: 2rem; border-bottom: 1px solid var(--color-border); }}
    .post-header .post-meta {{ margin-bottom: 1rem; }}
    .post-header h1 {{ margin-bottom: 1rem; }}
    .post-intro {{ font-size: 1.15rem; color: var(--color-text-muted); max-width: 55ch; margin-top: 0; }}
    .post-content h2 {{ margin-top: 2.5rem; margin-bottom: 1rem; }}
    .post-content p {{ max-width: none; margin-top: 1rem; }}
    .post-content blockquote {{ border-left: 3px solid var(--color-accent); margin: 2rem 0; padding: 0.5rem 0 0.5rem 1.5rem; font-style: italic; color: var(--color-text-muted); border-radius: 0; }}
    .post-content a {{ color: var(--color-accent); text-decoration: underline; text-underline-offset: 3px; }}
    .post-content img {{ width: 100%; border-radius: var(--radius); margin: 2rem 0; }}
    .post-content ul {{ margin: 1rem 0 1rem 1.25rem; }}
    .post-content li {{ margin-top: 0.35rem; }}
    .post-footer {{ margin-top: 4rem; padding-top: 2rem; border-top: 1px solid var(--color-border); display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap; }}
    .post-footer a {{ font-size: 0.9rem; color: var(--color-text-muted); transition: color 150ms ease; }}
    .post-footer a:hover {{ color: var(--color-accent); }}
  </style>
</head>

<body>

  <nav class="nav">
    <div class="nav-inner">
      <a href="../index.html" class="nav-logo">In Transit</a>
      <ul class="nav-links">
        <li><a href="../about.html">About</a></li>
        <li><a href="index.html" class="active">Blog</a></li>
        <li><a href="https://stephen-bosch.com">Stephen</a></li>
        <li><a href="../contact.html">Contact</a></li>
      </ul>
    </div>
  </nav>


  <!-- This page was generated from "{source}" by tools/build_posts.py.
       Edit the Word document and run the script again, rather than
       editing this file by hand. -->
  <article class="post-body">

    <a href="index.html" class="post-back">← All posts</a>

    <header class="post-header">
      <div class="post-meta">
        <time datetime="{iso}">{long_date}</time>{tag_html}
      </div>
      <h1>{title_esc}</h1>{intro_html}
      <p style="font-size: 0.8rem; color: var(--color-text-muted); margin-top: 0.75rem;">
        By <strong>{author_esc}</strong>
      </p>
    </header>


    <div class="post-content">

      {content}

    </div>


    <footer class="post-footer">
      <a href="index.html">← All posts</a>{next_html}
    </footer>

  </article>


  <footer class="footer">
    <div class="container">
      <div class="footer-inner">
        <p>© <span id="year"></span> Stephen Bosch &amp; Liz Barranco</p>
        <nav class="footer-links">
          <a href="../about.html">About</a>
          <a href="index.html">Blog</a>
          <a href="https://stephen-bosch.com">Stephen</a>
          <a href="../contact.html">Contact</a>
        </nav>
      </div>
    </div>
  </footer>

  <script>document.getElementById('year').textContent = new Date().getFullYear();</script>

</body>
</html>
"""


def write_post_page(post, newer):
    tag_html = ""
    if post["tag"]:
        tag_html = (
            '\n        <span class="post-tag" style="margin-left: 0.75rem;">'
            "%s</span>" % html.escape(post["tag"])
        )

    intro_html = ""
    if post["excerpt"]:
        intro_html = '\n      <p class="post-intro">\n        %s\n      </p>' % (
            html.escape(post["excerpt"])
        )

    next_html = ""
    if newer:
        next_html = '\n      <a href="%s.html">Next post →</a>' % newer["slug"]

    page = POST_TEMPLATE.format(
        title_esc=html.escape(post["title"]),
        excerpt_attr=html.escape(post["excerpt"] or post["title"], quote=True),
        author_esc=html.escape(post["author"]),
        iso=post["date"].strftime("%Y-%m-%d"),
        long_date=post["date"].strftime("%-d %B %Y"),
        tag_html=tag_html,
        intro_html=intro_html,
        content=post["content"] or "<p></p>",
        next_html=next_html,
        source=html.escape(post["source"]),
    )

    path = os.path.join(BLOG_DIR, post["slug"] + ".html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
    return path


# ---------------------------------------------------------------------------
# REBUILDING THE POST LISTS
# ---------------------------------------------------------------------------

START = "<!-- POSTS:START - generated by tools/build_posts.py. Do not edit by hand. -->"
END = "<!-- POSTS:END -->"


def card_html(post, prefix, indent):
    tag = ""
    if post["tag"]:
        tag = '\n%s    <span class="post-tag">%s</span>' % (
            indent, html.escape(post["tag"])
        )
    excerpt = html.escape(post["excerpt"]) if post["excerpt"] else ""
    link = "%s%s.html" % (prefix, post["slug"])

    return (
        '{i}<article class="post-card">\n'
        '{i}  <div class="post-meta">\n'
        '{i}    <time datetime="{iso}">{short}</time>{tag}\n'
        '{i}  </div>\n'
        '{i}  <h3 class="post-title">\n'
        '{i}    <a href="{link}">{title}</a>\n'
        '{i}  </h3>\n'
        '{i}  <p class="post-excerpt">\n'
        '{i}    {excerpt}\n'
        '{i}  </p>\n'
        '{i}  <p class="post-author">By {author}</p>\n'
        '{i}  <a href="{link}" class="read-more">Read more →</a>\n'
        '{i}</article>'
    ).format(
        i=indent,
        iso=post["date"].strftime("%Y-%m-%d"),
        short=post["date"].strftime("%-d %b %Y"),
        tag=tag,
        link=link,
        title=html.escape(post["title"]),
        excerpt=excerpt,
        author=html.escape(post["author"]),
    )


def replace_region(path, cards, indent):
    with open(path, encoding="utf-8") as f:
        page = f.read()

    block = "%s\n%s\n%s%s" % (
        START,
        "\n\n".join(cards) if cards else indent + "<!-- No posts yet. -->",
        indent,
        END,
    )

    if START in page and END in page:
        page = re.sub(
            re.escape(START) + r".*?" + re.escape(END),
            lambda _: block,
            page,
            flags=re.S,
        )
    else:
        # First run: drop the generated block in place of the existing cards.
        match = re.search(
            r'(<div class="post-grid">\s*\n)(.*?)(\n\s*</div>)', page, re.S
        )
        if not match:
            print("  ! Could not find the post grid in %s" % os.path.basename(path))
            return False
        page = page[: match.start(2)] + indent + block + page[match.end(2):]

    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
    return True


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else DROP_FOLDER

    if not os.path.isdir(folder):
        print("Could not find the drop folder:\n  %s" % folder)
        print("\nCreate it, or pass a different folder:")
        print("  python3 tools/build_posts.py '/path/to/folder'")
        return 1

    docs = sorted(
        os.path.join(folder, n)
        for n in os.listdir(folder)
        if n.lower().endswith(".docx") and not n.startswith("~$")
    )

    if not docs:
        print("No Word documents found in:\n  %s" % folder)
        return 0

    print("Reading %d document(s) from %s\n" % (len(docs), folder))

    posts = []
    for path in docs:
        try:
            post = parse_post(path)
        except Exception as exc:  # noqa: BLE001 - show the user a clean message
            print("  SKIPPED %s\n    %s\n" % (os.path.basename(path), exc))
            continue
        posts.append(post)
        print(
            "  OK  %-40s -> blog/%s.html  (%d photo%s)"
            % (
                post["source"],
                post["slug"],
                post["images"],
                "" if post["images"] == 1 else "s",
            )
        )

    if not posts:
        print("\nNothing to build.")
        return 1

    # Newest first
    posts.sort(key=lambda p: p["date"], reverse=True)

    os.makedirs(BLOG_DIR, exist_ok=True)
    for index, post in enumerate(posts):
        newer = posts[index - 1] if index > 0 else None
        write_post_page(post, newer)

    # Blog page: every post. Home page: the three most recent.
    blog_cards = [card_html(p, "", " " * 8) for p in posts]
    home_cards = [card_html(p, "blog/", " " * 8) for p in posts[:3]]

    replace_region(os.path.join(BLOG_DIR, "index.html"), blog_cards, " " * 8)
    replace_region(os.path.join(SITE_ROOT, "index.html"), home_cards, " " * 8)

    print("\nBuilt %d post(s)." % len(posts))
    print("Updated blog/index.html and index.html.")
    print("\nNow commit and push in GitHub Desktop to publish.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
