# `anytype.Space`

## Download an image block

Image blocks expose their backing file object as `file_id`. This is distinct
from the block's own `id`. Images on objects retrieved through a space can be
downloaded directly:

```python
from pathlib import Path

import anytype

wine = space.get_object(wine_id)
image = next(block for block in wine.blocks if isinstance(block, anytype.Image))

data = image.download()
Path("wine.jpg").write_bytes(data)
```

Pass a non-negative pixel width to request an image variant, or use the space
method directly. A width of `0` explicitly selects the original image.

```python
thumbnail = image.download(width=320)
original = space.download_file(image.file_id, width=0)
```

::: anytype.Space
