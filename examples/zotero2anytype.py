import os
import sys
import time
import sqlite3
import json
import urllib.parse
from bs4 import BeautifulSoup

path = os.path.dirname(__file__)
sys.path.append(path + "/..")
import anytype

any = anytype.Anytype()
any.auth()


# Paths
ZOTERO_DB = "/home/neimog/Zotero/zotero.sqlite"
ZOTERO_STORAGE = "/home/neimog/Zotero/storage"


def parse_zotero_note(html_content):
    """Parses a single Zotero HTML note into a list of annotation dictionaries."""
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    parsed_annotations = []

    for p in soup.find_all("p"):
        highlight_span = p.find("span", class_="highlight")
        citation_span = p.find("span", class_="citation-item")

        if highlight_span:
            quote = highlight_span.get_text(strip=True).strip('“”"')
            meta_json_str = urllib.parse.unquote(highlight_span.get("data-annotation", "{}"))

            try:
                metadata = json.loads(meta_json_str)
            except json.JSONDecodeError:
                metadata = {}

            citation = citation_span.get_text(strip=True) if citation_span else ""

            parsed_annotations.append(
                {
                    "quote": quote,
                    "citation": citation,
                    "page": metadata.get("pageLabel"),
                    "color": metadata.get("color"),
                }
            )

    # If it's just a regular text note (no highlights), capture the raw text
    if not parsed_annotations:
        text = soup.get_text(strip=True)
        if text:
            parsed_annotations.append({"text_note": text})

    return parsed_annotations


def get_field(cur, item_id, field_name):
    """Helper to fetch a specific field for an item."""
    cur.execute(
        """
        SELECT v.value 
        FROM itemData d
        JOIN itemDataValues v ON v.valueID = d.valueID
        JOIN fields f ON f.fieldID = d.fieldID
        WHERE d.itemID=? AND f.fieldName=?
        LIMIT 1;
    """,
        (item_id, field_name),
    )
    row = cur.fetchone()
    return row[0] if row else None


def main():
    # Connect in read-only mode
    conn = sqlite3.connect(f"file:{ZOTERO_DB}?mode=ro", uri=True)
    cur = conn.cursor()

    # Get all PDF attachments
    cur.execute("""
        SELECT itemID, parentItemID, path
        FROM itemAttachments
        WHERE contentType='application/pdf';
    """)
    attachments = cur.fetchall()

    results = []

    for attachID, parentID, path in attachments:
        # Resolve path safely
        if path:
            if path.startswith("storage:"):
                key = path.split("storage:")[1]
                pdf_full = os.path.join(ZOTERO_STORAGE, key)
            else:
                pdf_full = path  # Absolute or linked file
        else:
            pdf_full = ""

        # Filter: Skip if the file doesn't actually exist on the local disk

        # Use parentID if it's an attachment, or attachID if it's a standalone PDF
        target_id = parentID if parentID else attachID

        # Fetch Metadata
        title = get_field(cur, target_id, "title")
        doi = get_field(cur, target_id, "DOI")
        year = get_field(cur, target_id, "date")

        # Fetch Authors
        cur.execute(
            """
            SELECT c.firstName, c.lastName 
            FROM itemCreators ic
            JOIN creators c ON c.creatorID = ic.creatorID
            WHERE ic.itemID=?
            ORDER BY ic.orderIndex ASC;
        """,
            (target_id,),
        )
        authors = ["{} {}".format(fn or "", ln or "").strip() for fn, ln in cur.fetchall()]

        # Fetch Notes (Using native itemNotes table)
        cur.execute(
            """
            SELECT note 
            FROM itemNotes 
            WHERE itemID IN (SELECT itemID FROM items WHERE parentItemID = ?)
        """,
            (target_id,),
        )
        raw_notes = [row[0] for row in cur.fetchall()]
        parsed_notes = []
        for raw_note in raw_notes:
            parsed_notes.extend(parse_zotero_note(raw_note))

        # Append to results
        results.append(
            {
                "title": title,
                "doi": doi,
                "year": year,
                "authors": authors,
                "notes": parsed_notes,
                "pdf": pdf_full,
            }
        )

    conn.close()
    return results


if __name__ == "__main__":
    results = main()

    any = anytype.Anytype()
    any.auth()

    api_space = any.get_spaces()[0]

    page_type = api_space.get_type_byname("Page")
    for r in results:
        obj = anytype.Object(r["title"])

        if len(r["notes"]) > 0:
            needadd = False
            for n in r["notes"]:
                if "text_note" in n:
                    obj.add_bullet(n["text_note"])
                    needadd = True
                if "quote" in n:
                    obj.add_bullet(n["quote"])
                    needadd = True
            if needadd:
                print(f"Adding {r["title"]}")
                api_space.create_object(obj, type=page_type)
            time.sleep(0.3)
