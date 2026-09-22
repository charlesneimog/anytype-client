from .api import apiEndpoints, APIWrapper


class Template(APIWrapper):
    def __init__(self):
        self._apiEndpoints: apiEndpoints | None = None
        self.type = ""
        self.id = ""
        self.name = ""
        self.icon = ""

    @classmethod
    def _from_api(cls, api, data):
        from .block import Block
        obj = cls()
        obj._apiEndpoints = api
        for key, value in data.items():
            if key == "blocks":
                value = [Block.from_dict(b) for b in value]
            setattr(obj, key, value)
        obj.name = data.get("properties", {}).get("name", data.get("name", ""))
        return obj

    def __repr__(self):
        return f"<Template(name={self.name}, icon={self.icon})>"
