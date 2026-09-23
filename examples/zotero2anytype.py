"""Import Zotero PDF reading notes as Anytype API v2 blocks.

Install: pip install -e '.[zotero]'
Preview: python examples/zotero2anytype.py --dry-run
Import:  python examples/zotero2anytype.py --space SPACE_ID

Reads the database without modifying it. Creates one page per bibliographic item
with notes; repeated runs create new pages. PDF files themselves are not uploaded.
"""
import argparse
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3
import sys
import urllib.parse

from bs4 import BeautifulSoup, Comment, NavigableString

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import anytype

ZOTERO_DB = "~/Zotero/zotero.sqlite"
ZOTERO_STORAGE = "~/Zotero/storage"

# Zotero's standard annotation palette -> Anytype background color tokens.
# Anytype uses a fixed palette, so exact RGB shades cannot be retained.
COLORS = {
    "#ffd400": "yellow", "#ff6666": "red", "#5fb236": "lime",
    "#2ea8e5": "blue", "#a28ae5": "purple", "#e56eee": "pink",
    "#f19837": "orange", "#aaaaaa": "grey",
}


def annotation_color(value):
    """Map Zotero hex colors (including custom shades) to the nearest palette color."""
    if not isinstance(value, str):
        return None
    value = value.strip().lower()
    if value in COLORS.values():
        return value
    if value in {"gray", "green"}:
        return {"gray": "grey", "green": "lime"}[value]
    if re.fullmatch(r"#[0-9a-f]{3}", value):
        value = "#" + "".join(c * 2 for c in value[1:])
    if not re.fullmatch(r"#[0-9a-f]{6}", value):
        return None
    def rgb(color):
        return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
    source = rgb(value)
    closest = min(COLORS, key=lambda c: sum((a - b) ** 2 for a, b in zip(source, rgb(c))))
    return COLORS[closest]


def plain_text(element):
    # Preserve inline word boundaries and explicit HTML paragraph/line breaks.
    for br in element.find_all("br"):
        br.replace_with("\n")
    return element.get_text().strip()


def parse_zotero_note(html_content):
    """Preserve highlights, citations, and surrounding prose from Zotero HTML."""
    soup = BeautifulSoup(html_content or "", "html.parser")
    result = []
    pending = []
    consumed_citations = set()

    def flush():
        text = "".join(pending).strip()
        if text and text not in {"()", "( )"}:
            result.append({"text_note": text})
        pending.clear()

    def visit(node):
        if isinstance(node, NavigableString):
            if not isinstance(node, Comment):
                pending.append(str(node))
            return
        if id(node) in consumed_citations or node.name in {"script", "style"}:
            return
        if node.name == "br":
            pending.append("\n")
            return
        if "highlight" in node.get("class", []):
            flush()
            try:
                metadata = json.loads(urllib.parse.unquote(node.get("data-annotation", "{}")))
            except (ValueError, TypeError):
                metadata = {}
            if not isinstance(metadata, dict):
                metadata = {}
            citation = node.find_next_sibling("span", class_="citation")
            if citation is None and len(node.parent.select(".highlight")) == 1:
                citation = node.parent.select_one(".citation, .citation-item")
            style = re.search(r"background(?:-color)?\s*:\s*(#[0-9a-fA-F]{3,6})\b",
                              node.get("style", ""))
            quote = plain_text(node).strip('“”"')
            if quote:
                result.append({"quote": quote,
                               "citation": plain_text(citation) if citation else "",
                               "page": metadata.get("pageLabel"),
                               "color": metadata.get("color") or (style.group(1) if style else None),
                               "annotation_key": metadata.get("annotationKey")})
                if citation:
                    consumed_citations.add(id(citation))
            return
        boundary = node.name in {"p", "li", "div", "h1", "h2", "h3", "blockquote"}
        if boundary:
            flush()
        for child in list(node.children):
            visit(child)
        if boundary:
            flush()

    visit(soup)
    flush()
    return result


def get_field(cur, item_id, field_name):
    row = cur.execute("""
        SELECT v.value FROM itemData d
        JOIN itemDataValues v ON v.valueID = d.valueID
        JOIN fields f ON f.fieldID = d.fieldID
        WHERE d.itemID=? AND f.fieldName=? LIMIT 1
    """, (item_id, field_name)).fetchone()
    return row[0] if row else None


def resolve_pdf_path(path, key, storage, linked_base=None):
    if not path:
        return ""
    if path.startswith("storage:"):
        return str(Path(storage).expanduser() / key / path[len("storage:"):])
    if path.startswith("attachments:"):
        return (str(Path(linked_base).expanduser() / path[len("attachments:"):])
                if linked_base else "")
    return str(Path(path).expanduser())


def main(db_path=ZOTERO_DB, storage=None, linked_base=None):
    """Read native annotations and HTML notes, grouped by parent item."""
    db = Path(db_path).expanduser().resolve()
    storage = storage or db.parent / "storage"
    with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)) as conn:
        conn.execute("BEGIN")  # A consistent read snapshot, including Zotero's WAL.
        cur = conn.cursor()
        tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        deleted = ({r[0] for r in cur.execute("SELECT itemID FROM deletedItems")}
                   if "deletedItems" in tables else set())
        attachments = cur.execute("""
            SELECT a.itemID, a.parentItemID, a.path, i.key
            FROM itemAttachments a JOIN items i ON i.itemID=a.itemID
            WHERE a.contentType='application/pdf' ORDER BY a.itemID
        """).fetchall()
        grouped = {}
        for attachment_id, parent_id, path, key in attachments:
            target_id = parent_id or attachment_id
            if attachment_id in deleted or target_id in deleted:
                continue
            grouped.setdefault(target_id, []).append((attachment_id, path, key))
        results = []
        for target_id, pdfs in grouped.items():
            authors = [" ".join(filter(None, row)).strip() for row in cur.execute("""
                SELECT c.firstName, c.lastName FROM itemCreators ic
                JOIN creators c ON c.creatorID=ic.creatorID
                WHERE ic.itemID=? ORDER BY ic.orderIndex
            """, (target_id,))]
            notes = []
            native_by_key = {}
            if "itemAnnotations" in tables:
                for attachment_id, _, _ in pdfs:
                    rows = cur.execute("""
                        SELECT a.itemID, i.key, a.text, a.comment, a.color, a.pageLabel
                        FROM itemAnnotations a JOIN items i ON i.itemID=a.itemID
                        WHERE a.parentItemID=? ORDER BY a.sortIndex, a.itemID
                    """, (attachment_id,)).fetchall()
                    for item_id, key, text, comment, color, page in rows:
                        if item_id in deleted or not (text or comment):
                            continue
                        annotation = {"quote": text or "", "comment": comment or "",
                                      "color": color, "page": page, "annotation_key": key}
                        notes.append(annotation)
                        native_by_key[key] = annotation
            owners = {target_id, *(pdf[0] for pdf in pdfs)}
            placeholders = ",".join("?" for _ in owners)
            for item_id, html in cur.execute(
                f"SELECT itemID, note FROM itemNotes WHERE parentItemID IN ({placeholders}) "
                "ORDER BY itemID", tuple(owners)
            ).fetchall():
                if item_id in deleted:
                    continue
                for note in parse_zotero_note(html):
                    native = native_by_key.get(note.get("annotation_key"))
                    if native is not None and note.get("quote") == native["quote"]:
                        if note.get("citation"):
                            native["citation"] = note["citation"]
                        continue
                    notes.append(note)
            paths = [resolve_pdf_path(path, key, storage, linked_base) for _, path, key in pdfs]
            results.append({"title": get_field(cur, target_id, "title") or "Untitled Zotero item",
                            "doi": get_field(cur, target_id, "DOI"),
                            "year": get_field(cur, target_id, "date"), "authors": authors,
                            "notes": notes, "pdf": paths[0], "pdfs": paths})
        return results


def literal_text(text):
    """Escape Markdown metacharacters because AnyBlock parses inline Markdown."""
    return re.sub(r"([\\`*_{}\[\]<>])", r"\\\1", str(text))


def build_object(record, type_key="page"):
    obj = anytype.Object(record["title"], type=type_key)
    for label, value in (("Authors", "; ".join(record.get("authors", []))),
                         ("Date", record.get("year")), ("DOI", record.get("doi"))):
        if value:
            obj.add_block(anytype.Text(literal_text(f"{label}: {value}")))
    for note in record["notes"]:
        color = annotation_color(note.get("color"))
        style = {"background_color": color} if color else {}
        if note.get("quote"):
            obj.add_block(anytype.Quote(literal_text(note["quote"]), **style))
        if note.get("comment"):
            obj.add_block(anytype.Text(literal_text(note["comment"]), **style))
        if note.get("text_note"):
            obj.add_block(anytype.Text(literal_text(note["text_note"])))
        source = note.get("citation") or ""
        if note.get("page") is not None:
            source = " · ".join(filter(None, [source, f"Page {note['page']}"]))
        if source:
            obj.add_block(anytype.Text(literal_text(source)))
    return obj


def cli(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=ZOTERO_DB, help="Zotero SQLite database")
    parser.add_argument("--storage", help="Storage directory (default: beside the database)")
    parser.add_argument("--linked-base", help="Zotero linked attachment base directory")
    parser.add_argument("--space", help="Destination Anytype space ID")
    parser.add_argument("--type", default="page", help="Destination type key (default: page)")
    parser.add_argument("--dry-run", action="store_true", help="Print JSON without contacting Anytype")
    args = parser.parse_args(argv)
    records = [r for r in main(args.db, args.storage, args.linked_base) if r["notes"]]
    objects = [build_object(r, args.type) for r in records]
    if args.dry_run:
        print(json.dumps([obj.to_document() for obj in objects], indent=2, ensure_ascii=False))
        return
    if not objects:
        print("No PDF annotations or notes found.")
        return
    client = anytype.Anytype()
    client.auth()
    if args.space:
        space = client.get_space(args.space)
    else:
        spaces = client.get_spaces()
        if len(spaces) != 1:
            parser.error("Choose a destination with --space SPACE_ID. Available spaces: " +
                         ", ".join(f"{s.name} ({s.id})" for s in spaces))
        space = spaces[0]
    for obj in objects:
        created = space.create_object(obj)
        print(f"Added {obj.name}: {created.id}")


if __name__ == "__main__":
    cli()
