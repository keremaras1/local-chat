"""Single shared Jinja2Templates instance.

All routers import `templates` from here so that custom filters (markdown, etc.)
registered once in main.py are visible everywhere.
"""

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")
