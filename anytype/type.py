from .template import Template
from .api import apiEndpoints, APIWrapper
from .utils import requires_auth
from .property import Property
from .icon import Icon


class Type(APIWrapper):
    """
    The Type class is used to interact with and manage templates in a specific space. It allows for retrieving available templates, setting a specific template for a type, and handling template-related actions within the space.
    """

    def __init__(self, name: str = ""):
        self._all_templates = []
        self.type = ""
        self.space_id = ""
        self.id = ""
        self.name = name
        self.key = ""
        self.properties = {}

        # creation
        self.layout: str = "basic"
        self.plural_name: str = ""

        self._icon: Icon | dict = Icon()
        self.template_id = ""

        if name != "" and self._apiEndpoints:
            self.set_template(name)

    @classmethod
    def _from_api(cls, api, data):
        if "formatVersion" not in data:
            return super()._from_api(api, data)
        obj = cls()
        obj._apiEndpoints = api
        obj.space_id = data.get("space_id", "")
        obj.id = data.get("id", "")
        obj.name = data.get("properties", {}).get("name", "")
        settings = data.get("type_settings", {})
        obj.key = settings.get("api_key", data.get("internal_key", ""))
        obj.layout = settings.get("layout", "basic")
        obj.plural_name = settings.get("plural_name", "")
        obj.template_id = settings.get("default_template", "")
        if data.get("icon"):
            obj.icon = data["icon"]
        obj.properties = {}
        for definition in settings.get("property_definitions", []):
            if definition.get("format") not in Property._FACTORY:
                continue
            prop = Property._from_api(api, {"key": definition['property'],
                "name": definition.get('name', definition['property']),
                "format": definition['format'], "space_id": obj.space_id})
            obj.properties[prop.name] = prop
        return obj

    @property
    def icon(self):
        return self._icon

    @icon.setter
    def icon(self, value):
        if value is None:
            self._icon = Icon()
        elif isinstance(value, dict):
            icon = Icon()
            icon._update_with_json(value)
            self._icon = icon
        elif isinstance(value, Icon):
            self._icon = value
        else:
            raise Exception("Invalid icon")

    @icon.getter
    def icon(self):
        return self._icon

    @requires_auth
    def get_template_byname(self, name: str, offset: int = 0, limit: int = 100) -> Template:
        """
        Retrieves a template by its name.

        This method paginates through all available templates in the space
        until a template with the given name is found.

        Parameters:
            name (str): The name of the template to retrieve.
            offset (int, optional): The starting offset for pagination (default: 0).
            limit (int, optional): The maximum number of templates per request (default: 100).

        Returns:
            Template: The matching Template instance.

        Raises:
            ValueError: If no template with the given name is found.
            Raises an error if the request to the API fails.
        """
        while True:
            templates = self.get_templates(offset=offset, limit=limit)
            template_len = len(templates)

            for template in templates:
                if template.name == name:
                    return template

            if template_len < limit:
                break

            offset += limit

        raise ValueError("Template not found")

    @requires_auth
    def get_templates(
        self, offset: int = 0, limit: int = 100, filters: dict | None = None
    ) -> list[Template]:
        """
        Retrieves all templates associated with the type from the API.

        Parameters:
            offset (int): The offset to start retrieving templates (default: 0).
            limit (int): The maximum number of templates to retrieve (default: 100).

        Returns:
            A list of Template objects.

        Raises:
            Raises an error if the request to the API fails.
        """
        response = self._apiEndpoints.getTemplates(self.space_id, self.id, offset, limit, filters)
        self._all_templates = [
            Template._from_api(self._apiEndpoints, data | {"space_id": self.space_id})
            for data in response.get("data", [])
        ]

        return self._all_templates

    def set_template(self, template_name: str) -> None:
        """
        Sets a template for the type by name. If no templates are loaded, it will first fetch all templates.

        Parameters:
            template_name (str): The name of the template to assign.

        Returns:
            None

        Raises:
            ValueError: If a template with the specified name is not found.
        """
        if len(self._all_templates) == 0:
            self.get_templates()

        found = False
        for template in self._all_templates:
            if template.name == template_name:
                found = True
                self.template_id = template.id
                return
        if not found:
            raise ValueError(f"Type '{self.name}' does not have a template named '{template_name}'")

    @requires_auth
    def get_template(self, id: str) -> Template:
        """
        Retrieve a specific template by its unique identifier.

        Parameters:
            id (str): The unique identifier of the template to retrieve.

        Returns:
            Template: A `Template` instance populated with data retrieved from the API.

        Raises:
            Exception: If the request to the API fails or the template cannot be retrieved.
        """
        data = self._apiEndpoints.getTemplate(self.space_id, self.key, id)
        return Template._from_api(self._apiEndpoints, data | {"space_id": self.space_id})

    def add_property(self, property: Property) -> None:
        """
        Add a property definition to the type being constructed.

        If the API endpoints are not yet initialized (e.g., during local type definition),
        the property is added to the internal property list. Otherwise, the method is not implemented.

        Parameters:
            property (Property): `anytype.Property` to be added.

        Raises:
            Exception: If the API endpoints are initialized, indicating this functionality
                       is not yet supported in that context.
        """

        if self._apiEndpoints is None:
            self.properties[property.name] = property
        else:
            raise Exception("Not implemented yet")

    def __repr__(self):
        if self.icon:
            if self.icon.format == "emoji":
                return f"<Type(name={self.name}, icon={self.icon.emoji})>"
            else:
                return f"<Type(name={self.name}, icon={self.icon})>"
        return f"<Type(name={self.name})>"
