# Getting Started

## ☑️ Prerequisites

- Python 3.10+
- Anytype desktop app (v0.46.19-alpha or `higher`) running during authentication

## 📦 Installation

```bash
pip install anytype-client
``` 

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
new_note.add_text("This section was created programmatically using Python Anytype Client")

# Commit to workspace
created_object = my_space.create_object(new_note, note_type)
print(f"Created object: {created_object.id}")
```

## 🌟 Examples

| Example | Description | Results | 
|---------|-------------| ------  |
| [📄 Hello World](https://github.com/charlesneimog/anytype-client/examples/hello_world.py) | Create a basic note with formatted text | [Check Result](https://github.com/charlesneimog/anytype-client/resources/hello.png) |
| [📚 PDF Notes Importer](https://github.com/charlesneimog/anytype-client/examples/import-pdf-notes.py) | Batch import annotated PDFs | [Check Result](https://github.com/charlesneimog/anytype-client/resources/pdf.png) |
| *More examples coming as Anytype API evolves* | [Request a feature](https://github.com/charlesneimog/anytype-client/issues) | ⚔️ |
