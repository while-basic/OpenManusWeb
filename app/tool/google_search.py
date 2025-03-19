import asyncio
from typing import List, Union

from googlesearch import search

from app.tool.base import BaseTool
from app.logger import logger


class GoogleSearch(BaseTool):
    name: str = "google_search"
    description: str = """Perform a Google search and return a list of relevant links.
Use this tool when you need to find information on the web, get up-to-date data, or research specific topics.
The tool returns a list of URLs that match the search query.
"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "(required) The search query to submit to Google.",
            },
            "num_results": {
                "type": "integer",
                "description": "(optional) The number of search results to return. Default is 10.",
                "default": 10,
            },
        },
        "required": ["query"],
    }

    async def execute(self, query: str, num_results: Union[int, str] = 10) -> List[str]:
        """
        Execute a Google search and return a list of URLs.

        Args:
            query (str): The search query to submit to Google.
            num_results (Union[int, str], optional): The number of search results to return. 
                                                    Can be int or str. Default is 10.

        Returns:
            List[str]: A list of URLs matching the search query.
        """
        # Ensure num_results is an integer
        try:
            num_results_int = int(num_results)
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid num_results value: {num_results}, using default 10. Error: {e}")
            num_results_int = 10

        # Run the search in a thread pool to prevent blocking
        loop = asyncio.get_event_loop()
        links = await loop.run_in_executor(
            None, lambda: list(search(query, num_results=num_results_int))
        )

        return links
