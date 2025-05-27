from anytype import Anytype
from anytype import Object
from anytype import Type

from pdfannots import process_file
from pdfminer.layout import LAParams
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument


any = Anytype()
any.auth()

spaces = any.get_spaces()
pdf_space = None
found = False
for space in spaces:
    if space.name == "API":
        pdf_space = space
        found = True

if not found:
    pdf_space = any.create_space("API")


# After you are safe, add this to your main space (in my Anytype, my docs, and notes are the space[0])
# pdf_space = spaces[0]

all_notes = []
pdf_file = input("Enter the path to the pdf file: ")

pdf_name = pdf_file.split("/")[-1]
pdf_name = pdf_name.split(".")[0]

laparams = LAParams()
with open(pdf_file, "rb") as fp:
    doc = process_file(fp, laparams=laparams)
    parser = PDFParser(fp)
    document = PDFDocument(parser)
    metadata = document.info[0]  # metadata is a list of dictionaries

for page in doc.pages:
    pageNumber = page.pageno
    for annot in page.annots:
        result = {}
        result["page"] = pageNumber
        result["text"] = annot.gettext(True)
        result["contents"] = annot.contents
        result["author"] = annot.author

        if result["text"] is not None:
            result["text"] = result["text"].replace("\n", " ")
        all_notes.append(result)

if pdf_space is None:
    raise ValueError("Space not found")

# <- Not sure if this exists for you too
article_type = Type("Article")
article_type = pdf_space.create_type(article_type)
new_object = Object(pdf_name, article_type)
new_object.icon = "📄"
new_object.description = "This is an object created from Python Api"

for note in all_notes:
    new_object.body += f"> {note['text']} \n\n"

created_object = pdf_space.create_object(new_object)
