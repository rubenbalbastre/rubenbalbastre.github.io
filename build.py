#!/usr/bin/env python3
from __future__ import annotations

import html
import re
import shutil
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs"
PAGES = ROOT / "pages"
ASSETS = ROOT / "assets"

SITE_TITLE = "Rubén Balbastre"
SITE_DESCRIPTION = "AI research engineering, LLM post-training, agentic systems, and technical writing."


@dataclass
class MarkdownPage:
    source: Path
    front_matter: dict[str, str]
    body: str


@dataclass
class BlogPost:
    source: Path
    slug: str
    title: str
    date: str
    body_html: str


def parse_markdown(path: Path) -> MarkdownPage:
    text = path.read_text(encoding="utf-8")
    front_matter: dict[str, str] = {}

    if text.startswith("---\n"):
        _, raw_front_matter, body = text.split("---", 2)
        for line in raw_front_matter.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                front_matter[key.strip()] = value.strip().strip('"')
        text = body.lstrip("\n")

    return MarkdownPage(source=path, front_matter=front_matter, body=text)


def inline_markdown(text: str) -> str:
    text = text.replace("{{ site.baseurl }}", "")
    text = html.escape(text)

    text = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda match: (
            f'<img src="{match.group(2)}" alt="{html.escape(match.group(1), quote=True)}">'
        ),
        text,
    )
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda match: f'<a href="{match.group(2)}">{match.group(1)}</a>',
        text,
    )
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)
    return text


def markdown_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    output: list[str] = []
    paragraph: list[str] = []
    in_list = False
    i = 0

    def close_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            output.append(f"<p>{inline_markdown(' '.join(paragraph))}</p>")
            paragraph = []

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            output.append("</ul>")
            in_list = False

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if not stripped:
            close_paragraph()
            close_list()
            i += 1
            continue

        if stripped.startswith("<section"):
            close_paragraph()
            close_list()
            raw_block = [line]
            i += 1
            while i < len(lines):
                raw_block.append(lines[i].rstrip())
                if lines[i].strip() == "</section>":
                    i += 1
                    break
                i += 1
            output.append("\n".join(raw_block))
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            close_paragraph()
            close_list()
            level = len(heading.group(1))
            output.append(f"<h{level}>{inline_markdown(heading.group(2))}</h{level}>")
            i += 1
            continue

        if stripped.startswith("- "):
            close_paragraph()
            if not in_list:
                output.append("<ul>")
                in_list = True
            output.append(f"<li>{inline_markdown(stripped[2:])}</li>")
            i += 1
            continue

        paragraph.append(stripped)
        i += 1

    close_paragraph()
    close_list()
    return "\n".join(output)


def permalink_slug(page: MarkdownPage) -> str:
    permalink = page.front_matter.get("permalink", "")
    return permalink.strip("/").split("/")[-1]


def first_heading(markdown: str, level: int) -> str:
    marker = "#" * level
    for line in markdown.splitlines():
        if line.startswith(f"{marker} "):
            return line.removeprefix(f"{marker} ").strip().strip('"')
    return ""


def load_blog_posts() -> list[BlogPost]:
    posts: list[BlogPost] = []
    for path in sorted(PAGES.glob("blog_*.md"), reverse=True):
        page = parse_markdown(path)
        title = first_heading(page.body, 1)
        date = first_heading(page.body, 2)
        slug = permalink_slug(page)
        posts.append(
            BlogPost(
                source=path,
                slug=slug,
                title=title,
                date=date,
                body_html=markdown_to_html(page.body),
            )
        )
    return posts


def page(
    title: str,
    content: str,
    description: str = SITE_DESCRIPTION,
    wide: bool = False,
    lang: str = "en",
    extra_class: str = "",
    browser_title: str | None = None,
) -> str:
    shell_class = "page-shell page-shell-wide prose" if wide else "page-shell prose"
    if extra_class:
        shell_class = f"{shell_class} {extra_class}"
    return layout(
        title,
        f'<article class="{shell_class}">\n{content}\n</article>',
        description,
        lang=lang,
        browser_title=browser_title,
    )


def layout(
    title: str,
    content: str,
    description: str = SITE_DESCRIPTION,
    lang: str = "en",
    browser_title: str | None = None,
) -> str:
    full_title = browser_title or (f"{title} | {SITE_TITLE}" if title else SITE_TITLE)
    return f"""<!doctype html>
<html lang="{html.escape(lang, quote=True)}">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{html.escape(full_title)}</title>
    <meta name="description" content="{html.escape(description, quote=True)}">
    <link rel="stylesheet" href="/assets/css/site.css">
  </head>
  <body>
    <header class="site-header">
      <a class="brand" href="/" aria-label="{html.escape(SITE_TITLE, quote=True)}">
        <span class="brand-mark">RB</span>
        <span>{html.escape(SITE_TITLE)}</span>
      </a>
      <nav class="site-nav" aria-label="Main navigation">
        <a href="/">Home</a>
        <a href="/cv/">CV</a>
        <a href="/blog/">Blog</a>
        <a href="https://github.com/rubenbalbastre">GitHub</a>
        <a href="https://scholar.google.com/citations?user=QaOvwIQAAAAJ&amp;hl=en">Scholar</a>
        <a href="https://www.linkedin.com/in/rub%C3%A9n-balbastre-alcocer/">LinkedIn</a>
      </nav>
    </header>

    <main>
      {content}
    </main>

    <footer class="site-footer">
      <p>© 2026 {html.escape(SITE_TITLE)}. Published with GitHub Pages.</p>
    </footer>
  </body>
</html>
"""


def home_html(posts: list[BlogPost]) -> str:
    cards = "\n".join(
        f"""      <article class="post-card">
        <span class="date">{html.escape(post.date)}</span>
        <h3><a href="/blog/{post.slug}/">{html.escape(post.title)}</a></h3>
        <p>{html.escape(post_excerpt(post))}</p>
        <a class="read-more" href="/blog/{post.slug}/">Read article</a>
      </article>"""
        for post in posts[:4]
    )

    content = f"""<section class="home-hero-band">
  <div class="home-hero">
    <div>
      <p class="eyebrow">AI Research Engineer · LLM Post-Training · Agentic Systems</p>
      <h1>{html.escape(SITE_TITLE)}</h1>
      <p class="hero-positioning">I study how language models respond to post-training objectives and turn that understanding into dependable AI systems.</p>
      <div class="hero-actions">
        <a class="button" href="/cv/">View CV</a>
        <a class="button secondary" href="/blog/">Read blog</a>
      </div>
    </div>
    <div class="hero-visual">
      <img src="/assets/images/profile_image.jpeg" alt="Portrait of Rubén Balbastre">
    </div>
  </div>
</section>

<section class="section">
  <div class="section-inner">
    <div class="section-heading">
      <h2>What I Work On</h2>
      <p>Three threads connect my current research, industry experience, and technical writing.</p>
    </div>
    <div class="feature-grid">
      <div class="feature">
        <h3>LLM Post-Training Research</h3>
        <p>Research on GRPO/RLVR-style LLM unlearning, reward design, and evaluation reliability.</p>
        <a href="https://rubenbalbastre.github.io/grpo-unlearning-reward-specification/">Explore the project</a>
      </div>
      <div class="feature">
        <h3>Agentic Systems in Industry</h3>
        <p>Enterprise experience building supply-chain decision support with LLM agents, RAG, knowledge graphs, forecasting, and simulations.</p>
        <a href="/cv/">See industry experience</a>
      </div>
      <div class="feature">
        <h3>Technical Writing</h3>
        <p>Spanish essays on AI as technical, economic, and political infrastructure: labs, markets, energy, open source, and digital sovereignty.</p>
        <a href="/blog/">Browse the blog</a>
      </div>
    </div>
  </div>
</section>

<section class="section writing-band">
  <div class="section-inner">
    <div class="section-heading">
      <h2>Latest Writing</h2>
      <p>Recent Spanish essays from <em>El rincón de pensar</em>, my space for reflections on the evolution of artificial intelligence.</p>
    </div>
    <div class="post-grid">
{cards}
    </div>
  </div>
</section>
"""

    return layout("Home", content, "Personal website of Rubén Balbastre, an AI Research Engineer focused on LLM post-training and agentic systems.")


def post_excerpt(post: BlogPost) -> str:
    page = parse_markdown(post.source)
    body = re.sub(r"^# .*$", "", page.body, count=1, flags=re.MULTILINE)
    body = re.sub(r"^## .*$", "", body, count=1, flags=re.MULTILINE)
    body = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", body)
    for paragraph in body.split("\n\n"):
        clean = " ".join(paragraph.split())
        if clean and not clean.startswith("- "):
            return clean[:170].rstrip() + ("..." if len(clean) > 170 else "")
    return "Spanish article about artificial intelligence, product, and infrastructure."


def blog_index_html(posts: list[BlogPost]) -> str:
    groups: dict[str, list[BlogPost]] = {}
    for post in posts:
        year = post.slug.split("_", 1)[0]
        groups.setdefault(year, []).append(post)

    year_sections = []
    for year in sorted(groups, reverse=True):
        items = "\n".join(
            f"""    <li>
      <a href="/blog/{post.slug}/">{html.escape(post.title)}</a>
      <span>{html.escape(post.date)}</span>
    </li>"""
            for post in groups[year]
        )
        year_sections.append(
            f"""<section class="blog-year">
  <h2>{html.escape(year)}</h2>
  <ul class="blog-list">
{items}
  </ul>
</section>"""
        )

    grouped_posts = "\n\n".join(year_sections)
    content = f"""<header class="blog-index-header">
  <p class="blog-kicker">Blog</p>
  <h1>El rincón de pensar</h1>
  <p>Reflexiones sobre inteligencia artificial, tecnología y sus consecuencias prácticas. Estos escritos son mis aportaciones personales a la newsletter <a href="https://www.linkedin.com/newsletters/el-rinc%25C3%25B3n-de-los-datos-7062699750055157760/">“El rincón de los datos”</a>, creada por <a href="https://datamecum.com/">Datamecum</a> y coordinada por <a href="https://www.linkedin.com/in/emiliosoriaolivas/">Emilio Soria Olivas</a>.</p>
</header>

{grouped_posts}"""
    return page("El rincón de pensar", content, lang="es", extra_class="blog-index")


def blog_post_html(post: BlogPost) -> str:
    source = parse_markdown(post.source)
    body = re.sub(r"^# .*\n?", "", source.body, count=1, flags=re.MULTILINE)
    body = re.sub(r"^## .*\n?", "", body, count=1, flags=re.MULTILINE)
    content = f"""<header class="blog-post-header">
  <a class="back-link" href="/blog/">Blog</a>
  <p class="blog-kicker">El rincón de pensar</p>
  <h1>{html.escape(post.title)}</h1>
  <p class="blog-post-date">{html.escape(post.date)}</p>
</header>
<div class="blog-post-body">
{markdown_to_html(body)}
</div>"""
    return page(post.title, content, lang="es", extra_class="blog-post")


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build() -> None:
    posts = load_blog_posts()

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()

    shutil.copytree(ASSETS, OUT / "assets")
    write(OUT / ".nojekyll", "")
    write(OUT / "index.html", home_html(posts))

    cv_source = parse_markdown(PAGES / "cv.md")
    write(
        OUT / "cv" / "index.html",
        page(
            "CV",
            markdown_to_html(cv_source.body),
            "Professional CV of Rubén Balbastre.",
            wide=True,
            browser_title=f"{SITE_TITLE} | AI Research Engineer",
        ),
    )

    write(OUT / "blog" / "index.html", blog_index_html(posts))
    for post in posts:
        write(OUT / "blog" / post.slug / "index.html", blog_post_html(post))

    print(f"Built {OUT.relative_to(ROOT)} with {len(posts)} blog posts.")


if __name__ == "__main__":
    build()
