import asyncio
import json
import logging  # Add import
import time
from typing import Optional, Union

from browser_use import Browser as BrowserUseBrowser
from browser_use import BrowserConfig
from browser_use.browser.context import BrowserContext
from browser_use.dom.service import DomService
from pydantic import Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from app.tool.base import BaseTool, ToolResult


_BROWSER_DESCRIPTION = """
Interact with a web browser to perform various actions such as navigation, element interaction,
content extraction, and tab management. Supported actions include:
- 'navigate': Go to a specific URL
- 'click': Click an element by index
- 'input_text': Input text into an element
- 'screenshot': Capture a screenshot
- 'get_html': Get page HTML content
- 'get_text': Get text content of the page
- 'read_links': Get all links on the page
- 'execute_js': Execute JavaScript code
- 'scroll': Scroll the page
- 'switch_tab': Switch to a specific tab
- 'new_tab': Open a new tab
- 'close_tab': Close the current tab
- 'refresh': Refresh the current page
"""


class BrowserUseTool(BaseTool):
    name: str = "browser_use"
    description: str = _BROWSER_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "navigate",
                    "click",
                    "input_text",
                    "screenshot",
                    "get_html",
                    "get_text",
                    "execute_js",
                    "scroll",
                    "switch_tab",
                    "new_tab",
                    "close_tab",
                    "refresh",
                ],
                "description": "The browser action to perform",
            },
            "url": {
                "type": "string",
                "description": "URL for 'navigate' or 'new_tab' actions",
            },
            "index": {
                "type": "integer",
                "description": "Element index for 'click' or 'input_text' actions",
            },
            "text": {"type": "string", "description": "Text for 'input_text' action"},
            "script": {
                "type": "string",
                "description": "JavaScript code for 'execute_js' action",
            },
            "scroll_amount": {
                "type": "integer",
                "description": "Pixels to scroll (positive for down, negative for up) for 'scroll' action",
            },
            "tab_id": {
                "type": "integer",
                "description": "Tab ID for 'switch_tab' action",
            },
        },
        "required": ["action"],
        "dependencies": {
            "navigate": ["url"],
            "click": ["index"],
            "input_text": ["index", "text"],
            "execute_js": ["script"],
            "switch_tab": ["tab_id"],
            "new_tab": ["url"],
            "scroll": ["scroll_amount"],
        },
    }

    lock: asyncio.Lock = Field(default_factory=asyncio.Lock)
    browser: Optional[BrowserUseBrowser] = Field(default=None, exclude=True)
    context: Optional[BrowserContext] = Field(default=None, exclude=True)
    dom_service: Optional[DomService] = Field(default=None, exclude=True)

    @field_validator("parameters", mode="before")
    def validate_parameters(cls, v: dict, info: ValidationInfo) -> dict:
        if not v:
            raise ValueError("Parameters cannot be empty")
        return v

    async def _ensure_browser_initialized(self) -> BrowserContext:
        """Ensure browser and context are initialized."""
        if self.browser is None:
            self.browser = BrowserUseBrowser(BrowserConfig(headless=False))
        if self.context is None:
            self.context = await self.browser.new_context()
            self.dom_service = DomService(await self.context.get_current_page())
        return self.context

    async def execute(
        self,
        action: str,
        url: Optional[str] = None,
        index: Optional[Union[int, str]] = None,
        text: Optional[str] = None,
        script: Optional[str] = None,
        scroll_amount: Optional[Union[int, str]] = None,
        tab_id: Optional[Union[int, str]] = None,
        **kwargs,
    ) -> ToolResult:
        """
        Execute a specified browser action.

        Args:
            action: The browser action to perform
            url: URL for navigation or new tab
            index: Element index for click or input actions (can be int or str)
            text: Text for input action
            script: JavaScript code for execution
            scroll_amount: Pixels to scroll for scroll action (can be int or str)
            tab_id: Tab ID for switch_tab action (can be int or str)
            **kwargs: Additional arguments

        Returns:
            ToolResult with the action's output or error
        """
        # Convert string parameters to appropriate types if needed
        index_int = None
        scroll_amount_int = None
        tab_id_int = None
        
        if index is not None:
            try:
                index_int = int(index)
            except (ValueError, TypeError) as e:
                return ToolResult(error=f"Invalid index: {index}. Error: {e}")
                
        if scroll_amount is not None:
            try:
                scroll_amount_int = int(scroll_amount)
            except (ValueError, TypeError) as e:
                return ToolResult(error=f"Invalid scroll_amount: {scroll_amount}. Error: {e}")
                
        if tab_id is not None:
            try:
                tab_id_int = int(tab_id)
            except (ValueError, TypeError) as e:
                return ToolResult(error=f"Invalid tab_id: {tab_id}. Error: {e}")
        
        async with self.lock:
            try:
                context = await self._ensure_browser_initialized()

                if action == "navigate":
                    if not url:
                        return ToolResult(error="URL is required for 'navigate' action")
                    await context.navigate_to(url)
                    return ToolResult(output=f"Navigated to {url}")

                elif action == "click":
                    if index_int is None:
                        return ToolResult(error="Index is required for 'click' action")
                    element = await context.get_dom_element_by_index(index_int)
                    if not element:
                        return ToolResult(error=f"Element with index {index_int} not found")
                    download_path = await context._click_element_node(element)
                    output = f"Clicked element at index {index_int}"
                    if download_path:
                        output += f" - Downloaded file to {download_path}"
                    return ToolResult(output=output)

                elif action == "input_text":
                    if index_int is None or not text:
                        return ToolResult(
                            error="Index and text are required for 'input_text' action"
                        )
                    element = await context.get_dom_element_by_index(index_int)
                    if not element:
                        return ToolResult(error=f"Element with index {index_int} not found")
                    await context._input_text_element_node(element, text)
                    return ToolResult(
                        output=f"Input '{text}' into element at index {index_int}"
                    )

                elif action == "screenshot":
                    # Add temporary filename generation if not provided
                    filename = f"screenshot_{int(time.time())}.png"
                    path = await context.take_screenshot(filename)
                    return ToolResult(
                        output=f"Screenshot saved to {path}", file_paths=[path]
                    )

                elif action == "get_html":
                    html = await context.get_content()
                    return ToolResult(
                        output=f"Retrieved HTML content ({len(html)} characters)"
                    )

                elif action == "get_text":
                    text = await context.get_text_content()
                    return ToolResult(output=text)

                elif action == "read_links":
                    links = await context.get_link_elements()
                    formatted_links = []
                    for i, link in enumerate(links):
                        text = await link.get_text() or "[No text]"
                        href = await link.get_attribute("href") or "[No href]"
                        formatted_links.append(f"[{i}] {text}: {href}")
                    if not formatted_links:
                        return ToolResult(output="No links found on the page.")
                    return ToolResult(output="\n".join(formatted_links))

                elif action == "execute_js":
                    if not script:
                        return ToolResult(error="JavaScript code is required for 'execute_js' action")
                    result = await context.execute_javascript(script)
                    return ToolResult(
                        output=f"Executed JavaScript with result: {str(result)}"
                    )

                elif action == "scroll":
                    if scroll_amount_int is None:
                        return ToolResult(
                            error="Scroll amount is required for 'scroll' action"
                        )
                    await context.execute_javascript(
                        f"window.scrollBy(0, {scroll_amount_int});"
                    )
                    direction = "down" if scroll_amount_int > 0 else "up"
                    return ToolResult(
                        output=f"Scrolled {direction} by {abs(scroll_amount_int)} pixels"
                    )

                elif action == "switch_tab":
                    if tab_id_int is None:
                        return ToolResult(
                            error="Tab ID is required for 'switch_tab' action"
                        )
                    await context.switch_to_tab(tab_id_int)
                    return ToolResult(output=f"Switched to tab {tab_id_int}")

                elif action == "new_tab":
                    if not url:
                        return ToolResult(error="URL is required for 'new_tab' action")
                    tab_id = await context.new_tab(url)
                    return ToolResult(output=f"Opened new tab (ID: {tab_id}) with URL: {url}")

                elif action == "close_tab":
                    await context.close_current_tab()
                    return ToolResult(output="Closed current tab")

                elif action == "refresh":
                    await context.refresh()
                    return ToolResult(output="Refreshed current page")

                else:
                    return ToolResult(error=f"Unknown action: {action}")

            except Exception as e:
                logging.error(f"BrowserUseTool error: {e}")
                return ToolResult(error=f"Browser error: {str(e)}")

    async def get_current_state(self) -> ToolResult:
        """Get the current state of the browser."""
        if self.context is None or self.dom_service is None:
            return ToolResult(error="Browser not initialized")

        try:
            url = await self.context.get_url()
            title = await self.dom_service.get_title()
            
            # Get tabs information
            tabs = await self.context.get_tabs()
            tabs_info = []
            for i, tab in enumerate(tabs):
                tab_url = await tab.get_url()
                tab_title = await tab.get_title() or "No title"
                tabs_info.append(f"[{i}] {tab_title}: {tab_url}")

            current_tab_index = await self.context.get_current_tab_index()
            
            # Get basic page stats
            elements_count = await self.dom_service.get_elements_count()
            links_count = await self.dom_service.get_links_count()
            
            # Format output
            output = [
                f"Current URL: {url}",
                f"Page Title: {title}",
                f"Current Tab: {current_tab_index}",
                f"Total Tabs: {len(tabs)}",
                f"Elements on page: {elements_count}",
                f"Links on page: {links_count}",
                "\nAvailable Tabs:",
            ]
            output.extend(tabs_info)
            
            return ToolResult(output="\n".join(output))
        except Exception as e:
            logging.error(f"Error getting browser state: {e}")
            return ToolResult(error=f"Error getting browser state: {str(e)}")

    async def close(self):
        """Close the browser and clean up resources."""
        if self.browser:
            try:
                await self.browser.close()
            except Exception as e:
                logging.error(f"Error closing browser: {e}")
            finally:
                self.browser = None
                self.context = None
                self.dom_service = None

    async def cleanup(self):
        """Clean up resources when the tool is no longer needed."""
        await self.close()

    def __del__(self):
        """Destructor to ensure resources are cleaned up."""
        if hasattr(self, "browser") and self.browser is not None:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
                else:
                    # Create a new event loop if needed
                    new_loop = asyncio.new_event_loop()
                    new_loop.run_until_complete(self.close())
                    new_loop.close()
            except Exception as e:
                logging.error(f"Error in browser cleanup during destruction: {e}")
                if hasattr(self, "browser"):
                    self.browser = None
                if hasattr(self, "context"):
                    self.context = None
                if hasattr(self, "dom_service"):
                    self.dom_service = None
