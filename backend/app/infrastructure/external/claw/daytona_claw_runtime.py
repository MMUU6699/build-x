import asyncio
import logging
from typing import Optional

import httpx

from app.domain.external.claw import ClawInstanceInfo
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class DaytonaClawRuntime:
    """Creates claw instances as Daytona cloud containers."""

    creates_immediately = False

    def __init__(self):
        self.settings = get_settings()

    async def create(self, claw_id: str, api_key: str) -> ClawInstanceInfo:
        from daytona import Daytona, DaytonaConfig, CreateSandboxFromImageParams

        daytona_config = DaytonaConfig(api_key=self.settings.daytona_api_key) if self.settings.daytona_api_key else DaytonaConfig()
        daytona = Daytona(daytona_config)

        build_x_api_base_url = self.settings.build_x_api_base_url
        env_vars = {
            "CLAW_TTL_SECONDS": str(self.settings.claw_ttl_seconds),
            "BUILD_X_API_KEY": api_key,
            "BUILD_X_API_BASE_URL": build_x_api_base_url,
        }

        sandbox = daytona.create(
            CreateSandboxFromImageParams(
                image=self.settings.claw_image,
                env_vars=env_vars,
            )
        )

        p_18788 = sandbox.get_preview_link(18788)
        address = p_18788.url.rstrip("/")

        logger.info(f"Daytona claw container started: id={sandbox.id} address={address}")
        return ClawInstanceInfo(address=address, instance_name=sandbox.id)

    async def destroy(self, instance_name: Optional[str]) -> None:
        if not instance_name:
            return
        try:
            from daytona import Daytona, DaytonaConfig

            daytona_config = DaytonaConfig(api_key=self.settings.daytona_api_key) if self.settings.daytona_api_key else DaytonaConfig()
            daytona = Daytona(daytona_config)
            daytona.delete(instance_name)
            logger.info(f"Removed Daytona claw container: {instance_name}")
        except Exception as e:
            logger.warning(f"Failed to remove Daytona claw container {instance_name}: {e}")

    async def wait_for_ready(self, base_url: str) -> bool:
        timeout = self.settings.claw_ready_timeout
        interval = 2.0
        max_retries = int(timeout / interval)
        async with httpx.AsyncClient(timeout=5.0) as client:
            for _ in range(max_retries):
                try:
                    resp = await client.get(f"{base_url}/health")
                    if resp.status_code == 200:
                        logger.info(f"Claw instance ready: {base_url}")
                        return True
                except Exception:
                    pass
                await asyncio.sleep(interval)
        logger.warning(f"Claw instance health check timed out: {base_url}")
        return False
