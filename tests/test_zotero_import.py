"""Offline importer regression tests: python -m unittest discover -s tests -p test_zotero_import.py."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from urllib.parse import quote
from unittest.mock import patch

try:
    import bs4
except ImportError:
    raise unittest.SkipTest("Install the zotero extra to test the importer")

spec = importlib.util.spec_from_file_location(
    "zotero_import", Path(__file__).resolve().parents[1] / "examples/zotero2anytype.py"
)
zotero = importlib.util.module_from_spec(spec)
spec.loader.exec_module(zotero)


def highlight(text="A highlight", key="ANNOTATION"):
    metadata = quote(json.dumps({"annotationKey": key, "color": "#ffd400", "pageLabel": "iv"}))
    return (f'<span class="highlight" data-annotation="{metadata}">“{text}”</span>'
            '<span class="citation">(Author, 2024)</span>')


class ZoteroImportTests(unittest.TestCase):
    def test_standard_and_custom_colors(self):
        for value, expected in zotero.COLORS.items():
            self.assertEqual(zotero.annotation_color(value.upper()), expected)
        self.assertEqual(zotero.annotation_color("#ffd401"), "yellow")
        self.assertEqual(zotero.annotation_color("#aaa"), "grey")
        self.assertIsNone(zotero.annotation_color("invalid"))
        self.assertIsNone(zotero.annotation_color(None))

    def test_mixed_html_preserves_prose_and_multiple_highlights(self):
        notes = zotero.parse_zotero_note(
            '<div><p>My <em>reading</em> note</p><p>' + highlight() +
            ' My comment</p><p>' + highlight("Second", "SECOND") + '</p></div>'
        )
        self.assertEqual([n["quote"] for n in notes if "quote" in n], ["A highlight", "Second"])
        self.assertEqual([n["text_note"] for n in notes if "text_note" in n],
                         ["My reading note", "My comment"])
        self.assertEqual(notes[1]["page"], "iv")
        self.assertEqual(notes[1]["citation"], "(Author, 2024)")

    def test_malformed_metadata_and_css_fallback(self):
        for metadata in ("broken", "null", "[]"):
            notes = zotero.parse_zotero_note(
                f'<p><span class="highlight" data-annotation="{metadata}" '
                'style="background-color: #ff6666">Keep <b>this</b> text</span></p>'
            )
            self.assertEqual(notes[0]["quote"], "Keep this text")
            self.assertEqual(notes[0]["color"], "#ff6666")

    def test_nested_notes_keep_text_in_document_order(self):
        notes = zotero.parse_zotero_note(
            '<div>Intro<p>Before ' + highlight() + ' After</p>End</div>'
        )
        self.assertEqual([n.get("quote", n.get("text_note")) for n in notes],
                         ["Intro", "Before", "A highlight", "After", "End"])

    def test_v2_blocks_preserve_literal_text_and_metadata(self):
        obj = zotero.build_object({"title": "Paper", "notes": [
            {"quote": "a_b * c", "color": "#2ea8e5", "comment": "My comment", "page": "iv"},
            {"text_note": "Regular note"},
        ]})
        document = obj.to_document()
        self.assertEqual(document["formatVersion"], "2.0")
        self.assertEqual(document["type"], "page")
        self.assertEqual(document["blocks"][0], {
            "type": "quote", "text": r"a\_b \* c", "background_color": "blue"})
        self.assertEqual(document["blocks"][1]["text"], "My comment")
        self.assertEqual(document["blocks"][2]["text"], "Page iv")
        self.assertEqual(document["blocks"][3]["type"], "paragraph")

    def test_attachment_paths(self):
        self.assertEqual(zotero.resolve_pdf_path("storage:paper.pdf", "KEY", "/z/storage"),
                         "/z/storage/KEY/paper.pdf")
        self.assertEqual(zotero.resolve_pdf_path("attachments:folder/p.pdf", "KEY", "/z", "/base"),
                         "/base/folder/p.pdf")
        self.assertEqual(zotero.resolve_pdf_path("/absolute/p.pdf", "KEY", "/z"), "/absolute/p.pdf")

    def make_database(self, path):
        with contextlib.closing(sqlite3.connect(path)) as conn, conn:
            conn.executescript('''
                CREATE TABLE items (itemID INTEGER, key TEXT);
                CREATE TABLE itemAttachments (itemID INTEGER, parentItemID INTEGER, path TEXT, contentType TEXT);
                CREATE TABLE itemAnnotations (itemID INTEGER, parentItemID INTEGER, text TEXT,
                    comment TEXT, color TEXT, pageLabel TEXT, sortIndex TEXT);
                CREATE TABLE itemNotes (itemID INTEGER, parentItemID INTEGER, note TEXT);
                CREATE TABLE deletedItems (itemID INTEGER);
                CREATE TABLE itemData (itemID INTEGER, fieldID INTEGER, valueID INTEGER);
                CREATE TABLE itemDataValues (valueID INTEGER, value TEXT);
                CREATE TABLE fields (fieldID INTEGER, fieldName TEXT);
                CREATE TABLE itemCreators (itemID INTEGER, creatorID INTEGER, orderIndex INTEGER);
                CREATE TABLE creators (creatorID INTEGER, firstName TEXT, lastName TEXT);
                INSERT INTO items VALUES (1, 'PARENT'), (2, 'PDFONE'), (3, 'PDFTWO'),
                    (4, 'ANNOTATION'), (5, 'DELETED'), (6, 'STANDALONE');
                INSERT INTO itemAttachments VALUES (2, 1, 'storage:a.pdf', 'application/pdf'),
                    (3, 1, 'storage:b.pdf', 'application/pdf'),
                    (6, NULL, '/missing.pdf', 'application/pdf');
                INSERT INTO fields VALUES (1, 'title');
                INSERT INTO itemDataValues VALUES (1, 'Paper');
                INSERT INTO itemData VALUES (1, 1, 1);
                INSERT INTO itemAnnotations VALUES (4, 2, 'A highlight', 'Native comment', '#ffd400', 'iv', '1'),
                    (5, 2, 'Deleted highlight', '', '#ff6666', 'v', '2');
                INSERT INTO deletedItems VALUES (5), (11);
                INSERT INTO itemNotes VALUES (10, 3, '<p>Attachment note</p>'),
                    (11, 1, '<p>Deleted note</p>'), (12, 6, '<p>Standalone note</p>');
            ''')
            conn.execute("INSERT INTO itemNotes VALUES (9, 1, ?)", ('<p>' + highlight() + '</p>',))

    def test_database_grouping_native_notes_deletion_and_offline_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "zotero.sqlite"
            self.make_database(path)
            before = path.read_bytes()
            records = zotero.main(path)
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]["title"], "Paper")
            self.assertEqual(len(records[0]["pdfs"]), 2)
            self.assertEqual(len(records[0]["notes"]), 2)
            self.assertEqual(records[0]["notes"][0]["comment"], "Native comment")
            self.assertEqual(records[0]["notes"][0]["citation"], "(Author, 2024)")
            self.assertEqual(records[1]["notes"], [{"text_note": "Standalone note"}])
            self.assertEqual(path.read_bytes(), before)
            output = io.StringIO()
            with patch.object(zotero.anytype, "Anytype", side_effect=AssertionError("Unexpected API")):
                with contextlib.redirect_stdout(output):
                    zotero.cli(["--db", str(path), "--dry-run"])
            self.assertEqual(len(json.loads(output.getvalue())), 2)
            with contextlib.closing(sqlite3.connect(path)) as conn, conn:
                conn.execute("DROP TABLE itemAnnotations")
            self.assertEqual(zotero.main(path)[0]["notes"][0]["quote"], "A highlight")


if __name__ == "__main__":
    unittest.main()
