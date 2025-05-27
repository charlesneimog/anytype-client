from .template import Template
from .api import apiEndpoints, APIWrapper
from .utils import requires_auth, _ANYTYPE_SYSTEM_RELATIONS
from .property import (
    Property,
    Checkbox,
    Text,
    Number,
    Select,
    MultiSelect,
    Date,
    Files,
    Url,
    Email,
    Phone,
    Objects,
)
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

        # creation
        self.layout: str = ""
        self.plural_name: str = ""

        self._icon: Icon | dict = {}
        self._properties: list[Property | dict] = []
        self._properties_value: list = []
        self.template_id = ""

        if name != "" and self._apiEndpoints:
            self.set_template(name)

    @property
    def properties(self):
        return self._properties

    @properties.setter
    def properties(self, value):
        self._properties = []
        self._properties_value = value

    @properties.getter
    def properties(self):
        if len(self._properties) > 0:
            return self._properties

        for prop in self._properties_value:
            id = prop["id"]
            response = self._apiEndpoints.getProperty(self.space_id, id)
            data = response.get("property", {})
            format = data["format"]
            if format == "checkbox":
                prop = Checkbox._from_api(self._apiEndpoints, data | {"space_id": self.space_id})
            elif format == "text":
                prop = Text._from_api(self._apiEndpoints, data | {"space_id": self.space_id})
            elif format == "number":
                prop = Number._from_api(self._apiEndpoints, data | {"space_id": self.space_id})
            elif format == "select":
                prop = Select._from_api(self._apiEndpoints, data | {"space_id": self.space_id})
            elif format == "multi_select":
                prop = MultiSelect._from_api(self._apiEndpoints, data | {"space_id": self.space_id})
            elif format == "date":
                prop = Date._from_api(self._apiEndpoints, data | {"space_id": self.space_id})
            elif format == "files":
                prop = Files._from_api(self._apiEndpoints, data | {"space_id": self.space_id})
            elif format == "url":
                prop = Url._from_api(self._apiEndpoints, data | {"space_id": self.space_id})
            elif format == "email":
                prop = Email._from_api(self._apiEndpoints, data | {"space_id": self.space_id})
            elif format == "phone":
                prop = Phone._from_api(self._apiEndpoints, data | {"space_id": self.space_id})
            elif format == "objects":
                prop = Objects._from_api(self._apiEndpoints, data | {"space_id": self.space_id})
            else:
                raise Exception("Invalid format")

            if prop.key in _ANYTYPE_SYSTEM_RELATIONS:
                continue
            self._properties.append(prop)
        return self._properties

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
    def get_templates(self, offset: int = 0, limit: int = 100) -> list[Template]:
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
        response = self._apiEndpoints.getTemplates(self.space_id, self.id, offset, limit)
        self._all_templates = [
            Template._from_api(self._apiEndpoints, data) for data in response.get("data", [])
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
        response_data = self._apiEndpoints.getTemplate(self.space_id, self.id, id)

        template = Template()
        template._apiEndpoints = self._apiEndpoints
        for data in response_data.get("data", []):
            for key, value in data.items():
                template.__dict__[key] = value

        return template

    def add_property(self, property: Property) -> None:
        """
        Add a property definition to the type being constructed.

        If the API endpoints are not yet initialized (e.g., during local type definition),
        the property is added to the internal property list. Otherwise, the method is not implemented.

        Parameters:
            name (str): The name of the property to add.
            property_format (PropertyFormat): The format of the property (e.g., text, number, date).

        Returns:
            None

        Raises:
            Exception: If the API endpoints are initialized, indicating this functionality
                       is not yet supported in that context.
        """

        if self._apiEndpoints is None:
            prop = {"format": property.format, "name": property.name}  # or: property_format.value
            self.properties.append(prop)
        else:
            raise Exception("Not implemented yet")

    def __repr__(self):
        if self.icon:
            if self.icon.format == "emoji":
                return f"<Type(name={self.name}, icon={self.icon.emoji})>"
            else:
                return f"<Type(name={self.name}, icon={self.icon})>"
        return f"<Type(name={self.name})>"
