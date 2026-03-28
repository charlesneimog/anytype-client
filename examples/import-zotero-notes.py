import sys
import os

dir = os.path.dirname(os.path.abspath(__file__)) + "/../"
sys.path.insert(0, dir)

from anytype import Anytype, Object, Property

any = Anytype()
any.auth()

space = any.get_spaces()[0]

anypage = space.get_type_byname("Page")
anytemplate = anypage.get_template_byname("Reading Notes")


import sqlite3
import re
from pathlib import Path
from html import unescape

# ------------------------------------------------------------
# Paths (adjust to your Zotero setup)
# ------------------------------------------------------------
DB = "/home/neimog/Zotero/zotero.sqlite"
STORAGE = Path("/home/neimog/Zotero/storage")

# ------------------------------------------------------------
# Open DB in strict read-only mode
# ------------------------------------------------------------
conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
cur = conn.cursor()

# ------------------------------------------------------------
# Queries
# ------------------------------------------------------------
attachments_query = """
SELECT
    att.key AS attachment_key,
    att.itemID AS attachment_id,
    parent.key AS parent_key,
    parent.itemID AS parent_id
FROM itemAttachments ia
JOIN items att ON ia.itemID = att.itemID
JOIN items parent ON ia.parentItemID = parent.itemID
WHERE ia.contentType = 'application/pdf'
"""

field_query = """
SELECT v.value
FROM itemData d
JOIN itemDataValues v ON d.valueID = v.valueID
JOIN fields f ON d.fieldID = f.fieldID
JOIN items i ON d.itemID = i.itemID
WHERE i.key = ?
AND f.fieldName = ?
"""

extra_query = """
SELECT v.value
FROM itemData d
JOIN itemDataValues v ON d.valueID = v.valueID
JOIN fields f ON d.fieldID = f.fieldID
JOIN items i ON d.itemID = i.itemID
WHERE i.key = ?
AND f.fieldName = 'extra'
"""

# Notes (Zotero 7) – check both parent and attachment
notes_query = """
SELECT note
FROM itemNotes
WHERE parentItemID IN (?, ?)
"""

authors_query = """
SELECT 
    COALESCE(c.firstName, '') AS firstName,
    COALESCE(c.lastName, '') AS lastName,
    COALESCE(c.name, '') AS name
FROM itemCreators c
JOIN items i ON c.itemID = i.itemID
WHERE i.key = ?
AND c.creatorType = 'author'
ORDER BY c.orderIndex
"""

authors_query = """
SELECT
    cr.firstName,
    cr.lastName
FROM itemCreators ic
JOIN creators cr ON ic.creatorID = cr.creatorID
JOIN creatorTypes ct ON ic.creatorTypeID = ct.creatorTypeID
JOIN items i ON ic.itemID = i.itemID
WHERE i.key = ?
  AND ct.creatorType = 'author'
ORDER BY ic.orderIndex
"""


# ------------------------------------------------------------
# Regex for DOI / ISBN fallback
# ------------------------------------------------------------
doi_re = re.compile(r"DOI\s*:\s*(10\.\S+)", re.IGNORECASE)
isbn_re = re.compile(r"ISBN\s*:\s*([0-9Xx\-]+)", re.IGNORECASE)
html_tag_re = re.compile(r"<[^>]+>")


def clean_html(text: str) -> str:
    """Strip HTML tags and unescape entities."""
    text = unescape(text)
    return html_tag_re.sub("", text).strip()


# ------------------------------------------------------------
# Fetch attachments
# ------------------------------------------------------------
cur.execute(attachments_query)
attachments = cur.fetchall()

# ------------------------------------------------------------
# Iterate through attachments
# ------------------------------------------------------------

humans = []
offset = 0
persons_len = 100
human = space.get_type("Human")
while persons_len > 20:
    h_obj = space.get_objects(offset, 100)
    print(h_obj)
    for obj in h_obj:
        if obj.type is not None and obj.type.id == human.id:
            humans.append(obj)
    persons_len = len(h_obj)


humans_names = []
for h in humans:
    humans_names.append(h.name)

print(humans_names)

from pdfannots import process_file
from pdfminer.layout import LAParams

for attachment_key, attachment_id, parent_key, parent_id in attachments:
    # Title
    cur.execute(field_query, (parent_key, "title"))
    row = cur.fetchone()
    title = row[0] if row else "NO TITLE"

    # DOI
    cur.execute(field_query, (parent_key, "DOI"))
    row = cur.fetchone()
    doi = row[0] if row else None

    # ISBN
    cur.execute(field_query, (parent_key, "ISBN"))
    row = cur.fetchone()
    isbn = row[0] if row else None

    # Authors
    cur.execute(authors_query, (parent_key,))
    authors = []
    for first, last in cur.fetchall():
        name = f"{first} {last}".strip()
        authors.append(name)

    # Fallback: parse from "extra"
    if doi is None or isbn is None:
        cur.execute(extra_query, (parent_key,))
        row = cur.fetchone()
        if row:
            extra = row[0]
            if doi is None:
                m = doi_re.search(extra)
                if m:
                    doi = m.group(1)
            if isbn is None:
                m = isbn_re.search(extra)
                if m:
                    isbn = m.group(1)

    # Notes (both parent and attachment-level)
    cur.execute(notes_query, (parent_id, attachment_id))
    notes = [clean_html(r[0]) for r in cur.fetchall()]

    # PDF file
    folder = STORAGE / attachment_key
    if not folder.exists():
        continue

    pdfs = list(folder.glob("*.pdf"))
    if not pdfs:
        continue

    laparams = LAParams()
    with open(pdfs[0], "rb") as fp:
        doc = process_file(fp, columns_per_page=None, emit_progress_to=None, laparams=laparams)
        data = []
        for page in doc.pages:
            pageNumber = page.pageno
            for annot in page.annots:
                result = {}
                result["page"] = pageNumber
                result["text"] = annot.gettext(True)
                result["author"] = annot.author
                result["created"] = annot.created.strftime("%d-%m-%Y")
                result["color"] = annot.color.ashex()
                data.append(result)

        if len(data) != 0:
            authors_id = []
            for a in authors:
                if a not in humans_names:
                    new_human = Object(a)
                    obj = space.create_object(new_human, human)
                else:
                    for ao in humans:
                        if ao.name == a:
                            authors_id.append(ao)

            obj = Object(title, anypage, anytemplate)
            if doi is not None:
                obj.properties["DOI"].value = doi

            obj.properties["Author"].value = authors_id
            for d in data:
                obj.add_quote(d["text"])

            newobj = space.create_object(obj)


conn.close()
