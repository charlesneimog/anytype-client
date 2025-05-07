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
        self._apiEndpoints: apiEndpoints | None = None
        self._all_templates = []
        self.type = ""
        self.space_id = ""
        self.id = ""
        self.name = ""
        self._icon: Icon | dict = {}
        self._properties : list[Property] = []
        self.key = ""
        self.template_id = ""
        if name != "":
            self.set_template(name)

    @property
    def properties(self):
        return self._properties

    @properties.setter
    def properties(self, value):
        self._properties = []
        for prop in value:
            id = (prop["id"])
            response = self._apiEndpoints.getProperty(self.space_id, id)
            data = response.get("property", {})
            prop = Property._from_api(self._apiEndpoints, data | {"space_id": self.id})
            self._properties.append(prop)

    @properties.getter
    def properties(self):
        return self._properties

    @property
    def icon(self):
        return self._icon

    @icon.setter
    def icon(self, value):
        if isinstance(value, dict):
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
            raise ValueError(
                f"Type '{self.name}' does not have " "a template named '{template_name}'"
            )

    @requires_auth
    def get_template(self, id: str) -> Template:
        response_data = self._apiEndpoints.getTemplate(self.space_id, self.id, id)

        template = Template()
        template._apiEndpoints = self._apiEndpoints
        for data in response_data.get("data", []):
            for key, value in data.items():
                template.__dict__[key] = value

        return template

    def __repr__(self):
        if self.icon:
            if self.icon.format == "emoji":
                return f"<Type(name={self.name}, icon={self.icon.emoji})>"
            else:
                return f"<Type(name={self.name}, icon={self.icon})>"
        return f"<Type(name={self.name})>"
