import sys
import os
import html

# for my tests
file = os.path.dirname(__file__) + "/../"
sys.path.append(file)

import anytype
import requests
import time

any = anytype.Anytype()
any.auth()


spaces = any.get_spaces()

myspace = None
for space in spaces:
    if space.name == "My Space":
        myspace = space
        break

if myspace is None:
    myspace = any.create_space("My Space")


article_type = None
for type in myspace.get_types(offset=0, limit=100):
    if type.name == "Artigo":
        article_type = type

objects = myspace.search("", article_type)

# if type does not exist we create it
if article_type is None:
    article_type = anytype.Type("Artigo")
    article_type.icon = anytype.Icon()  # default icon
    article_type.layout = "basic"
    article_type.plural_name = "Artigos"

    article_type.add_property(anytype.property.Text("Doi"))
    article_type.add_property(anytype.property.Number("Publication Year"))
    article_type.add_property(anytype.property.MultiSelect("Authors"))
    article_type.add_property(anytype.property.Checkbox("Readed"))
    article_type = myspace.create_type(article_type)

assert isinstance(article_type, anytype.Type)


time.sleep(2)


def add_article(doi, recursive=False):
    url = f"https://api.crossref.org/works/{doi}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()

        # Article Metadata
        title = data["message"]["title"][0]
        authors = []
        for author in data.get("message", {}).get("author", []):
            if "given" not in author or "family" not in author:
                authors.append(author["name"])
            else:
                authors.append(f"{author['given']} {author['family']}")

        # Year and DOI of the article
        article_doi = data["message"]["URL"]
        year = data["message"]["issued"]["date-parts"][0][0]

        # Creating the article object
        obj = anytype.Object(title, article_type)
        obj.doi = article_doi
        authors = [html.unescape(author).title() for author in authors]  # fix encoding

        obj.properties["Doi"].value = article_doi
        obj.properties["Authors"].value = authors
        obj.properties["Publication Year"].value = year
        obj.properties["Readed"].value = False

        # Handle references (citations)
        references = data["message"].get("reference", [])

        if recursive:
            for reference in references:
                ref_doi = reference.get("DOI", "")
                if ref_doi != "":
                    add_article(ref_doi)

        myspace.create_object(obj)
        time.sleep(1)

    else:
        print(f"Error fetching article data: {response.status_code}")


# Example usage:
doi = "10.1080/17459737.2025.2465976"
add_article(doi, True)
