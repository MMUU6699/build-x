from typing import Dict, Any, Optional, List, BinaryIO
import uuid
import httpx
import logging
import asyncio
import io
from async_lru import alru_cache
from app.core.config import get_settings
from app.domain.models.tool_result import ToolResult
from app.domain.external.sandbox import Sandbox
from app.infrastructure.external.browser.playwright_browser import PlaywrightBrowser
from app.domain.external.browser import Browser

logger = logging.getLogger(__name__)


class DaytonaSandbox(Sandbox):
    """Daytona-backed sandbox implementation running containers on Daytona Cloud."""

    def __init__(
        self,
        sandbox_id: str,
        base_url: str,
        vnc_url: str,
        cdp_url: str,
        auth_headers: Optional[Dict[str, str]] = None,
    ):
        """Initialize Daytona sandbox client."""
        self._id = sandbox_id
        self.base_url = base_url.rstrip("/")
        self._vnc_url = vnc_url
        self._cdp_url = cdp_url
        self._auth_headers = auth_headers or {}
        self.client = httpx.AsyncClient(timeout=600, headers=self._auth_headers)

    @property
    def id(self) -> str:
        return self._id

    @property
    def cdp_url(self) -> str:
        return self._cdp_url

    @property
    def vnc_url(self) -> str:
        return self._vnc_url

    @classmethod
    async def create(cls) -> "DaytonaSandbox":
        """Create a new Daytona sandbox instance."""
        settings = get_settings()
        image = settings.sandbox_image or "ghcr.io/mmuu6699/build-x-sandbox:latest"

        env_vars = {
            "SERVICE_TIMEOUT_MINUTES": str(settings.sandbox_ttl_minutes or 30),
            "CHROME_ARGS": settings.sandbox_chrome_args or "",
        }
        if settings.sandbox_https_proxy:
            env_vars["HTTPS_PROXY"] = settings.sandbox_https_proxy
        if settings.sandbox_http_proxy:
            env_vars["HTTP_PROXY"] = settings.sandbox_http_proxy
        if settings.sandbox_no_proxy:
            env_vars["NO_PROXY"] = settings.sandbox_no_proxy

        try:
            try:
                from daytona import Daytona, DaytonaConfig, CreateSandboxFromImageParams
            except ImportError:
                from daytona_sdk import Daytona, DaytonaConfig, CreateSandboxFromImageParams

            if not settings.daytona_api_key:
                logger.info("DAYTONA_API_KEY not set. Using local sandbox fallback.")
                return cls(
                    sandbox_id="local-fallback-sandbox",
                    base_url="http://localhost:8080",
                    vnc_url="ws://localhost:5901",
                    cdp_url="http://localhost:9222",
                    auth_headers={},
                )

            daytona_config = DaytonaConfig(api_key=settings.daytona_api_key)
            daytona = Daytona(daytona_config)

            sandbox = daytona.create(
                CreateSandboxFromImageParams(
                    image=image,
                    env_vars=env_vars,
                )
            )

            p_8080 = sandbox.get_preview_link(8080)
            p_5901 = sandbox.get_preview_link(5901)
            p_9222 = sandbox.get_preview_link(9222)

            base_url = p_8080.url
            auth_token = getattr(p_8080, "token", None) or getattr(sandbox, "token", "")
            auth_headers = {"x-daytona-preview-token": auth_token} if auth_token else {}

            vnc_url = p_5901.url.replace("http://", "ws://").replace("https://", "wss://")
            cdp_url = p_9222.url

            instance = cls(
                sandbox_id=sandbox.id,
                base_url=base_url,
                vnc_url=vnc_url,
                cdp_url=cdp_url,
                auth_headers=auth_headers,
            )
            await instance.ensure_sandbox()
            return instance

        except Exception as e:
            logger.warning(f"Failed to create Daytona sandbox ({e}). Using local fallback.")
            return cls(
                sandbox_id="local-fallback-sandbox",
                base_url="http://localhost:8080",
                vnc_url="ws://localhost:5901",
                cdp_url="http://localhost:9222",
                auth_headers={},
            )

    @classmethod
    async def get(cls, sandbox_id: str) -> Optional["DaytonaSandbox"]:
        """Retrieve existing Daytona sandbox instance."""
        if sandbox_id == "local-fallback-sandbox":
            return cls(
                sandbox_id="local-fallback-sandbox",
                base_url="http://localhost:8080",
                vnc_url="ws://localhost:5901",
                cdp_url="http://localhost:9222",
                auth_headers={},
            )
            
        settings = get_settings()
        try:
            try:
                from daytona import Daytona, DaytonaConfig
            except ImportError:
                from daytona_sdk import Daytona, DaytonaConfig

            daytona_config = DaytonaConfig(api_key=settings.daytona_api_key) if settings.daytona_api_key else DaytonaConfig()
            daytona = Daytona(daytona_config)

            sandbox = daytona.get(sandbox_id)
            if not sandbox:
                return None

            p_8080 = sandbox.get_preview_link(8080)
            p_5901 = sandbox.get_preview_link(5901)
            p_9222 = sandbox.get_preview_link(9222)

            base_url = p_8080.url
            auth_token = getattr(p_8080, "token", None) or getattr(sandbox, "token", "")
            auth_headers = {"x-daytona-preview-token": auth_token} if auth_token else {}

            vnc_url = p_5901.url.replace("http://", "ws://").replace("https://", "wss://")
            cdp_url = p_9222.url

            return cls(
                sandbox_id=sandbox.id,
                base_url=base_url,
                vnc_url=vnc_url,
                cdp_url=cdp_url,
                auth_headers=auth_headers,
            )
        except Exception as e:
            logger.warning(f"Failed to get Daytona sandbox {sandbox_id}: {e}")
            return None

    async def ensure_sandbox(self) -> None:
        """Ensure sandbox is ready by checking supervisor status."""
        max_retries = 3
        retry_interval = 1

        for attempt in range(max_retries):
            try:
                response = await self.client.get(f"{self.base_url}/api/v1/supervisor/status")
                response.raise_for_status()

                tool_result = ToolResult(**response.json())
                if not tool_result.success:
                    await asyncio.sleep(retry_interval)
                    continue

                services = tool_result.data or []
                if services and all(s.get("statename") == "RUNNING" for s in services):
                    logger.info("Daytona sandbox services are RUNNING and ready")
                    return

                await asyncio.sleep(retry_interval)
            except Exception as e:
                logger.warning(f"Supervisor health check attempt {attempt + 1}/{max_retries} failed: {e}")
                await asyncio.sleep(retry_interval)

        logger.error("Daytona sandbox failed supervisor health check")

    async def destroy(self) -> None:
        """Destroy Daytona sandbox instance."""
        settings = get_settings()
        try:
            try:
                from daytona import Daytona, DaytonaConfig
            except ImportError:
                from daytona_sdk import Daytona, DaytonaConfig

            daytona_config = DaytonaConfig(api_key=settings.daytona_api_key) if settings.daytona_api_key else DaytonaConfig()
            daytona = Daytona(daytona_config)
            daytona.delete(self._id)
            logger.info(f"Daytona sandbox {self._id} deleted")
        except Exception as e:
            logger.warning(f"Error destroying Daytona sandbox {self._id}: {e}")
        finally:
            await self.client.aclose()

    async def get_browser(self, user_id: str = "anonymous") -> Browser:
        """Get browser instance connected to sandbox CDP."""
        settings = get_settings()
        engine = settings.browser_engine.lower()
        if engine == "browser_use":
            try:
                from app.infrastructure.external.browser.browser_use_browser import BrowserUseBrowser
                return BrowserUseBrowser(self.cdp_url, user_id)
            except Exception as e:
                logger.warning(f"BrowserUseBrowser error ({e}), using PlaywrightBrowser")
        return PlaywrightBrowser(self.cdp_url)

    async def exec_command(self, command: str, timeout: Optional[int] = None) -> ToolResult:
        payload = {"command": command, "timeout": timeout}
        res = await self.client.post(f"{self.base_url}/api/v1/shell/exec", json=payload)
        return ToolResult(**res.json())

    async def view_shell(self, session_id: str) -> ToolResult:
        res = await self.client.get(f"{self.base_url}/api/v1/shell/view/{session_id}")
        return ToolResult(**res.json())

    async def wait_for_process(self, session_id: str, timeout: Optional[int] = None) -> ToolResult:
        payload = {"session_id": session_id, "timeout": timeout}
        res = await self.client.post(f"{self.base_url}/api/v1/shell/wait", json=payload)
        return ToolResult(**res.json())

    async def write_to_process(self, session_id: str, data: str) -> ToolResult:
        payload = {"session_id": session_id, "data": data}
        res = await self.client.post(f"{self.base_url}/api/v1/shell/write", json=payload)
        return ToolResult(**res.json())

    async def kill_process(self, session_id: str) -> ToolResult:
        res = await self.client.post(f"{self.base_url}/api/v1/shell/kill/{session_id}")
        return ToolResult(**res.json())

    async def file_write(self, file_path: str, content: str) -> ToolResult:
        payload = {"file_path": file_path, "content": content}
        res = await self.client.post(f"{self.base_url}/api/v1/file/write", json=payload)
        return ToolResult(**res.json())

    async def file_read(self, file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> ToolResult:
        params = {"file_path": file_path}
        if start_line is not None:
            params["start_line"] = start_line
        if end_line is not None:
            params["end_line"] = end_line
        res = await self.client.get(f"{self.base_url}/api/v1/file/read", params=params)
        return ToolResult(**res.json())

    async def file_exists(self, file_path: str) -> ToolResult:
        res = await self.client.get(f"{self.base_url}/api/v1/file/exists", params={"file_path": file_path})
        return ToolResult(**res.json())

    async def file_delete(self, file_path: str) -> ToolResult:
        res = await self.client.delete(f"{self.base_url}/api/v1/file/delete", params={"file_path": file_path})
        return ToolResult(**res.json())

    async def file_list(self, dir_path: str) -> ToolResult:
        res = await self.client.get(f"{self.base_url}/api/v1/file/list", params={"dir_path": dir_path})
        return ToolResult(**res.json())

    async def file_replace(self, file_path: str, old_string: str, new_string: str) -> ToolResult:
        payload = {"file_path": file_path, "old_string": old_string, "new_string": new_string}
        res = await self.client.post(f"{self.base_url}/api/v1/file/replace", json=payload)
        return ToolResult(**res.json())

    async def file_search(self, dir_path: str, pattern: str) -> ToolResult:
        payload = {"dir_path": dir_path, "pattern": pattern}
        res = await self.client.post(f"{self.base_url}/api/v1/file/search", json=payload)
        return ToolResult(**res.json())

    async def file_find(self, dir_path: str, glob_pattern: str) -> ToolResult:
        payload = {"dir_path": dir_path, "glob_pattern": glob_pattern}
        res = await self.client.post(f"{self.base_url}/api/v1/file/find", json=payload)
        return ToolResult(**res.json())

    async def upload_file(self, file_path: str, file_content: bytes) -> ToolResult:
        files = {"file": (file_path, io.BytesIO(file_content))}
        res = await self.client.post(f"{self.base_url}/api/v1/file/upload", files=files, data={"file_path": file_path})
        return ToolResult(**res.json())

    async def download_file(self, file_path: str) -> ToolResult:
        res = await self.client.get(f"{self.base_url}/api/v1/file/download", params={"file_path": file_path})
        return ToolResult(**res.json())
