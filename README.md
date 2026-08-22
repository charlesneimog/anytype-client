# Anytype Python Client 

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-GPL3-green)](https://github.com/charlesneimog/anytype-client/blob/main/LICENSE)

A Python client for interacting with [Anytype](https://anytype.io/). Automate workflows and integrate with your apps! ✨

---

## 🚀 Features

- **Seamless Integration**: Connect Python scripts directly to your Anytype workspace.
- **Object Management**: Create, modify, and organize pages, notes, and custom objects.
- **Space Operations**: Manage spaces, types, and relations programmatically.
- **Batch Operations**: Export data, automate repetitive tasks, and more.
- **PDF Import Example**: Bulk import annotated PDFs as structured notes (see [examples](https://github.com/charlesneimog/anytype-client/tree/main/examples)).

---

## 📦 Installation

```bash
pip install anytype-client
``` 

### Prerequisites:

- Python 3.10+
- Anytype desktop app (v0.44.13-beta or higher) running during authentication

## ⚡ Quick Start

1. Authentication

``` python
from anytype import Anytype

# Initialize client (first run triggers authentication)
any = Anytype()
any.auth()  # 🔑 Enter 4-digit code from Anytype app when prompted
``` 
2. Create Your First Object

``` python
from anytype import Object

# Get your workspace
spaces = any.get_spaces()
my_space = spaces[0]  # Use your preferred space

# Create a new page
note_type = my_space.get_type("Page")
new_note = Object()
new_note.name = "My Python-Powered Note 📝"
new_note.icon = "🔥"
new_note.description = "Automatically generated via Python API"

# Add rich content
new_note.add_title1("Welcome to Automated Knowledge Management!")
new_note.add_text("This section was created programmatically using Python")

# Commit to workspace
created_object = my_space.create_object(new_note, note_type)
print(f"Created object: {created_object.name}")
```

### API 2025-11-08

List endpoints accept the API's dynamic filter syntax as a dictionary, global search
accepts the complete search body, and spaces expose chat listing and file upload:

```python
spaces = any.get_spaces(filters={"name[contains]": "project"})
pages = any.global_search(
    "roadmap",
    types=["page", "task"],
    sort={"direction": "desc", "property_key": "last_modified_date"},
)

chats = spaces[0].get_chats(limit=50)
uploaded = spaces[0].upload_file("./report.pdf")
objects = spaces[0].get_objects(
    filters={"type": "page", "created_date[gte]": "2024-01-01"}
)
```

## 🌟 Examples


| Example | Description | Results | 
|---------|-------------| ------  |
| [📄 Hello World](examples/hello_world.py) | Create a basic note with formatted text | [Check Result](resources/hello.png) |
| [🏷️ Custom properties](examples/custom-properties.py) | Create from a type and template with date and object properties | — |
| [🔌 API 2025-11-08](examples/api-2025-11-08.py) | Explore listing, search, tags, templates, upload, and list objects | — |
| [📚 PDF Notes Importer](examples/import-pdf-notes.py) | Batch import annotated PDFs | [Check Result](resources/pdf.png) |
| *More examples coming as Anytype API evolves* | [Request a feature](https://github.com/charlesneimog/anytype-client/issues) | ⚔️ |

## 📄 Documentation

Check the documentation [here](https://charlesneimog.github.io/anytype-client)!

## 🤝 Contributing

Contributions are welcomed! Here's how to help:

1. Report bugs or request features via Issues
2. Submit pull requests for improvements
3. Share your use cases in Discussions

## 📄 License

GPL-3.0 License - see LICENSE for details.
