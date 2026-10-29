"""
OpenAI Sora2 Video Generator

Provides an alternative generator to Google Veo 3 for YouTube Shorts.
Integrates with the Shorts orchestration pipeline without creating new modules.

WSP Compliance:
- WSP 17 (Pattern Registry) - reuse existing Move2Japan prompt enhancer
- WSP 46 (WRE Orchestration) - integrates through existing orchestrator cube
- WSP 84 (No Vibecoding) - builds on established Shorts module structure
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Optional

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class Sora2GenerationError(Exception):
    """Raised when Sora2 API generation fails."""


class Sora2Generator:
    """Thin wrapper around the OpenAI Sora2 video generation API."""

    def __init__(self, output_dir: Optional[str] = None) -> None:
        load_dotenv()

        # Check for Azure OpenAI endpoint (preferred) or fallback to OpenAI direct API
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if azure_endpoint:
            # Azure OpenAI configuration
            self.use_azure = True
            self.azure_endpoint = azure_endpoint.rstrip('/')
            self.api_key = os.getenv("AZURE_OPENAI_KEY")
            if not self.api_key:
                raise ValueError("AZURE_OPENAI_KEY must be set when using AZURE_OPENAI_ENDPOINT")
            self.api_url = f"{self.azure_endpoint}/openai/v1/video/generations/jobs"
            self.api_version = "preview"
            # Azure uses deployment names instead of model names
            self.deployment_name = os.getenv("AZURE_OPENAI_SORA_DEPLOYMENT", "sora")
            logger.info("[SORA2-INIT] Using Azure OpenAI endpoint")
            logger.info(f"[SORA2-INIT] Azure deployment: {self.deployment_name}")
        else:
            # OpenAI direct API (when available)
            self.use_azure = False
            api_key = os.getenv("SORA_API_KEY") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("SORA_API_KEY or OPENAI_API_KEY must be configured for Sora2 generation")
            self.api_key = api_key
            self.api_url = os.getenv("SORA_API_BASE_URL", "https://api.openai.com/v1/videos")
            self.deployment_name = None
            logger.info("[SORA2-INIT] Using OpenAI direct API (when available)")

        self.model = os.getenv("SORA2_MODEL", "sora")
        self.poll_interval = float(os.getenv("SORA2_POLL_INTERVAL", "5"))
        self.max_wait_seconds = int(os.getenv("SORA2_MAX_WAIT_SECONDS", "600"))
        self.cost_per_second = float(os.getenv("SORA2_COST_PER_SECOND", "0.80"))

        if output_dir is None:
            module_root = Path(__file__).parent.parent
            output_dir = module_root / "assets" / "generated"

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("[SORA2-INIT] Sora2 Generator initialised")
        logger.info("[SORA2-INIT] Output directory: %s", self.output_dir)
        logger.info("[SORA2-INIT] Model: %s", self.model)
        logger.info("[SORA2-INIT] Cost basis: $%s/second", self.cost_per_second)

    def enhance_prompt(self, simple_topic: str) -> str:
        """Reuse Move2Japan enhancer to keep tonal alignment."""

        try:
            from .prompt_enhancer import Move2JapanPromptEnhancer

            enhancer = Move2JapanPromptEnhancer()
            enhanced = enhancer.enhance(
                simple_topic,
                include_anti_maga=False,
                use_trending=True
            )
            logger.info("[SORA2-PROMPT] Enhanced topic via Move2Japan enhancer")
            return enhanced
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("[SORA2-PROMPT] Prompt enhancement failed: %s", exc)
            return simple_topic

    def generate_video(
        self,
        prompt: str,
        duration: int = 15,
        fast_mode: bool = True,
        aspect_ratio: str = "9:16"
    ) -> str:
        """Generate a single video clip via Sora2."""

        # Azure Sora supports 1-20 seconds
        if duration < 1 or duration > 20:
            logger.warning(f"[SORA2-GEN] Duration {duration}s out of range (1-20s), capping to 20s")
            duration = min(max(duration, 1), 20)

        # Map aspect ratio to Azure resolution (width x height)
        resolution_map = {
            "9:16": (1080, 1920),  # Vertical Shorts - 1080p
            "16:9": (1920, 1080),  # Horizontal - 1080p
            "1:1": (1080, 1080)    # Square - 1080p
        }
        width, height = resolution_map.get(aspect_ratio, (1080, 1920))

        if self.use_azure:
            # Azure OpenAI API format uses deployment name
            payload: Dict[str, object] = {
                "model": self.deployment_name,  # Azure uses deployment name here
                "prompt": prompt,
                "width": width,
                "height": height,
                "n_seconds": duration
            }
        else:
            # OpenAI direct API format (future)
            payload: Dict[str, object] = {
                "model": self.model,
                "prompt": prompt,
                "duration": duration,
                "aspect_ratio": aspect_ratio,
                "format": "mp4"
            }

        logger.info("[SORA2-GEN] Dispatching Sora2 job")
        logger.debug("[SORA2-GEN] Fast mode flag: %s", fast_mode)
        logger.info(f"[SORA2-GEN] Duration: {duration}s | Resolution: {width}x{height} ({aspect_ratio})")
        logger.info("[SORA2-GEN] Estimated cost: $%.2f", duration * self.cost_per_second)

        start_time = time.time()
        job_data = self._create_job(payload)
        job_id = job_data.get("id") or job_data.get("job_id")
        if not job_id:
            raise Sora2GenerationError("Sora2 API response missing job identifier")

        logger.info("[SORA2-GEN] Job ID: %s", job_id)

        status_data = self._poll_job(job_id)

        video_id = f"sora2_{int(time.time())}"
        output_path = self.output_dir / f"{video_id}.mp4"

        if self.use_azure:
            # Azure returns generation IDs, need separate API call to get video
            generations = status_data.get("generations", [])
            if not generations:
                raise Sora2GenerationError("No generations in Azure response")

            generation_id = generations[0].get("id")
            if not generation_id:
                raise Sora2GenerationError("No generation ID in Azure response")

            logger.info(f"[SORA2-GEN] Generation ID: {generation_id}")
            self._download_azure_video(generation_id, output_path)
        else:
            # OpenAI direct API returns video URL
            video_url = self._extract_video_url(status_data)
            if not video_url:
                raise Sora2GenerationError("Unable to extract video URL from Sora2 response")
            self._download_video(video_url, output_path)

        elapsed = time.time() - start_time
        logger.info("[SORA2-GEN] Video ready (%.1fs)", elapsed)
        logger.info("[SORA2-GEN] Saved to %s", output_path)

        metadata = {
            "video_id": video_id,
            "model": self.model,
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "cost": round(duration * self.cost_per_second, 2),
            "source": "sora2",
            "generated_at": time.time(),
            "status_payload": status_data
        }

        metadata_path = self.output_dir / f"{video_id}_meta.json"
        with open(metadata_path, "w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2)
        logger.info("[SORA2-GEN] Metadata saved to %s", metadata_path)

        return str(output_path)

    def generate_three_act_short(
        self,
        topic: str,
        duration: int = 15,
        fast_mode: bool = True,
        mode: str = "journal"
    ) -> str:
        """Generate a 3-act short by fusing prompts into one Sora2 request."""

        try:
            from .story_generator import ThreeActStoryGenerator
        except Exception as exc:  # pragma: no cover - defensive guard
            raise Sora2GenerationError(f"3-act story generator unavailable: {exc}") from exc

        story_builder = ThreeActStoryGenerator()
        story = story_builder.generate_story(topic)

        prompt = (
            "Create a 15-second vertical (9:16) cinematic video told in three acts. "
            f"Act 1 (Setup): {story['act1']}. "
            f"Act 2 (Shock): {story['act2']}. "
            f"Act 3 (0102 Reveal): {story['act3']}. "
            "Use the Move2Japan talking baby character, high energy pacing, vibrant colour grade, and "
            "smooth scene transitions between acts. Keep the final reveal playful and uplifting."
        )

        logger.info("[SORA2-3ACT] Story assembled for topic '%s'", topic)
        logger.info("[SORA2-3ACT] Prompt: %s", prompt[:140] + ("..." if len(prompt) > 140 else ""))

        return self.generate_video(
            prompt=prompt,
            duration=duration,
            fast_mode=fast_mode,
            aspect_ratio="9:16"
        )

    def _create_job(self, payload: Dict[str, object]) -> Dict[str, object]:
        if self.use_azure:
            # Azure OpenAI uses api-key header
            headers = {
                "api-key": self.api_key,
                "Content-Type": "application/json"
            }
            url = f"{self.api_url}?api-version={self.api_version}"
        else:
            # OpenAI direct API uses Bearer token
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            url = self.api_url

        try:
            logger.info(f"[SORA2-API] POST {url}")
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
            )
        except requests.RequestException as exc:
            raise Sora2GenerationError(f"Failed to reach Sora2 API: {exc}") from exc

        if response.status_code >= 400:
            raise Sora2GenerationError(
                f"Sora2 API error {response.status_code}: {response.text}"
            )

        return response.json()

    def _poll_job(self, job_id: str) -> Dict[str, object]:
        if self.use_azure:
            headers = {"api-key": self.api_key}
            status_url = f"{self.api_url}/{job_id}?api-version={self.api_version}"
        else:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            status_url = f"{self.api_url}/{job_id}"

        start_time = time.time()
        while True:
            try:
                response = requests.get(status_url, headers=headers, timeout=30)
            except requests.RequestException as exc:
                raise Sora2GenerationError(f"Sora2 status polling failed: {exc}") from exc

            if response.status_code >= 400:
                raise Sora2GenerationError(
                    f"Sora2 status error {response.status_code}: {response.text}"
                )

            data = response.json()
            status = (data.get("status") or data.get("state") or "").lower()
            logger.info("[SORA2-POLL] Job %s status: %s", job_id, status)

            if status in {"succeeded", "completed", "finished"}:
                return data
            if status in {"failed", "cancelled", "canceled", "error"}:
                raise Sora2GenerationError(f"Sora2 generation failed with status '{status}'")

            if time.time() - start_time > self.max_wait_seconds:
                raise Sora2GenerationError("Sora2 generation timed out")

            time.sleep(self.poll_interval)

    def _download_azure_video(self, generation_id: str, output_path: Path) -> None:
        """Download video from Azure OpenAI using generation ID."""
        headers = {"api-key": self.api_key}
        video_url = (
            f"{self.azure_endpoint}/openai/v1/video/generations/{generation_id}"
            f"/content/video?api-version={self.api_version}"
        )

        logger.info(f"[SORA2-DOWNLOAD] Fetching video from Azure: {video_url}")

        try:
            with requests.get(video_url, headers=headers, stream=True, timeout=60) as response:
                if response.status_code >= 400:
                    raise Sora2GenerationError(
                        f"Failed to download Azure video ({response.status_code}): {response.text}"
                    )

                with open(output_path, "wb") as handle:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            handle.write(chunk)

            logger.info(f"[SORA2-DOWNLOAD] Video saved: {output_path}")

        except requests.RequestException as exc:
            raise Sora2GenerationError(f"Azure video download failed: {exc}") from exc

    @staticmethod
    def _extract_video_url(data: Dict[str, object]) -> Optional[str]:
        result = data.get("result") or data.get("output")
        if isinstance(result, dict):
            outputs = result.get("outputs") or result.get("data") or result.get("assets")
            if isinstance(outputs, list):
                for item in outputs:
                    url = Sora2Generator._extract_url_from_item(item)
                    if url:
                        return url
            url = result.get("url") or result.get("video_url")
            if isinstance(url, str):
                return url

        for key in ("assets", "data", "outputs"):
            assets = data.get(key)
            if isinstance(assets, list):
                for item in assets:
                    url = Sora2Generator._extract_url_from_item(item)
                    if url:
                        return url

        for key in ("url", "video_url", "content_url"):
            direct = data.get(key)
            if isinstance(direct, str):
                return direct

        return None

    @staticmethod
    def _extract_url_from_item(item: object) -> Optional[str]:
        if isinstance(item, dict):
            for key in ("url", "video_url", "download_url", "content_url"):
                value = item.get(key)
                if isinstance(value, str):
                    return value
        return None

    @staticmethod
    def _download_video(video_url: str, output_path: Path) -> None:
        try:
            with requests.get(video_url, stream=True, timeout=60) as response:
                if response.status_code >= 400:
                    raise Sora2GenerationError(
                        f"Failed to download video ({response.status_code}): {response.text}"
                    )

                with open(output_path, "wb") as handle:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            handle.write(chunk)
        except requests.RequestException as exc:
            raise Sora2GenerationError(f"Video download failed: {exc}") from exc


__all__ = ["Sora2Generator", "Sora2GenerationError"]
