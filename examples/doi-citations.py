import anytype
import requests
import time

any = anytype.Anytype()
any.auth()

if len(any.get_spaces()) == 1:
    any.create_space("My Space")

space = any.get_spaces()[1]
types = space.get_types()
project_type = None
for type in types:
    if type.name == "Article":
        project_type = type
        break

if project_type is None:
    raise Exception("Article type not found")

import requests


def already_added(doi):
    listview = space.get_listviews(project_type)[0]
    print(listview)
    objects = listview.get_objectsinlistview()
    for obj in objects:
        print(obj)


def add_article(doi, recursive=False):
    url = f"https://api.crossref.org/works/{doi}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()

        # Article Metadata
        title = data["message"]["title"][0]
        authors = []
        for author in data.get("message", {}).get("author", []):
            authors.append(f"{author['given']} {author['family']}")

        # Year and DOI of the article
        article_doi = data["message"]["URL"]
        year = data["message"]["issued"]["date-parts"][0][0]

        # Creating the article object
        obj = anytype.Object(title, project_type)
        obj.doi = article_doi
        obj.author = authors
        obj.year = year

        # Handle references (citations)
        references = data["message"].get("reference", [])

        if recursive:
            for reference in references:
                ref_doi = reference.get("DOI", "")
                if ref_doi != "":
                    try:
                        add_article(ref_doi)
                    except Exception as e:
                        print(f"Failed to retrieve info about {doi} {e}")

        isOnList = False

        space.create_object(obj)
        time.sleep(0.5)

    else:
        print(f"Error fetching article data: {response.status_code}")


# Example usage:
doi = "10.1080/17459737.2025.2465976"
already_added(doi)
# add_article(doi, True)
