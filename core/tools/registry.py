import requests


class RegisteredTool:
    def __init__(
        self,
        name: str,
        description: str,  # i.e. the function docstring, instructs the agent how to use it
        endpoint: str,
        api_key: str = None,  # optional key for authentication if needed
        http_method: str = "POST",
        query_params: dict = None,
        body_format: str = "json",
        # optional: only return specified fields from API response
        return_fields: list = None,
        # TODO: make this more elegant like a Pydantic model or 2d list or something to handle nested properties and array indices
    ):
        self.name = name
        self.description = description
        self.endpoint = endpoint
        self.key = api_key
        self.http_method = http_method
        self.query_params = query_params if query_params else {}
        self.body_format = body_format
        self.return_fields = return_fields if return_fields else []

    def __repr__(self):
        s = f"Tool(name={self.name}, description={self.description}, endpoint={self.endpoint}"
        s += (
            (", return_fields=" + str(self.return_fields)) if self.return_fields else ""
        )
        return s + ")"

    def __filter_response(self, response_data: dict):
        """
        Filter the response data based on the specified return_fields.
        This method is used internally to process the API response.
        """
        if not self.return_fields:
            return response_data

        filtered_response = {}
        for field in self.return_fields:
            if field in response_data:
                filtered_response[field] = response_data[field]
        return filtered_response

    def __call__(self, *args, **kwargs):
        """
        Call the tool with the provided arguments and keyword arguments.
        This method should be overridden by subclasses to implement the tool's functionality.
        """
        req = {
            "method": self.http_method,
            "url": self.endpoint,
            "params": self.query_params,
            "headers": {},
        }
        if self.key:
            req["headers"]["Authorization"] = f"Bearer {self.key}"

        if self.body_format == "json":
            req["json"] = kwargs
        elif self.body_format == "form":
            req["data"] = kwargs
        else:
            raise ValueError(f"Unsupported body format: {self.body_format}")

        response = requests.request(**req)
        response.raise_for_status()
        response_data = response.json()

        response_data = self.__filter_response(response_data)
        return response_data


def main():
    poketool = RegisteredTool(
        name="pokemon_tool",
        description="A tool to fetch Pokemon data from an API.",
        # Example API endpoint (replace with actual)
        endpoint="https://pokeapi.co/api/v2/pokemon/pikachu",
        http_method="GET",
        return_fields=["weight", "location_area_encounters"],
    )
    print(f"poketool: {poketool}")

    response = poketool()
    print(response)


if __name__ == "__main__":
    main()
