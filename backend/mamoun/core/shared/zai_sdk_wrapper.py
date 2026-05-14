"""
Z-AI SDK Python Wrapper — Calls the Node.js z-ai-web-dev-sdk from Python.

The z-ai-web-dev-sdk is a Node.js module. This wrapper creates a bridge
so Python code can use web_search and web_reader functionality.

v58 — Super Mind العقل الخارق مامون
"""

import json
import subprocess
import tempfile
import os
import time
import logging
from typing import Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ── Node.js helper script ───────────────────────────────────────────────
_HELPER_SCRIPT = r"""
const ZAI = require('z-ai-web-dev-sdk');

async function main() {
    const args = JSON.parse(process.argv[2]);
    const zai = await ZAI.create();

    try {
        if (args.action === 'web_search') {
            const result = await zai.functions.invoke("web_search", {
                query: args.query,
                num: args.num || 10
            });
            // Result is an array of SearchFunctionResultItem
            const results = Array.isArray(result) ? result : [];
            console.log(JSON.stringify({success: true, data: results}));
        } else if (args.action === 'web_reader') {
            const result = await zai.functions.invoke("web_reader", {
                url: args.url
            });
            console.log(JSON.stringify({success: true, data: result}));
        } else if (args.action === 'chat') {
            const completion = await zai.chat.completions.create({
                messages: args.messages,
                max_tokens: args.max_tokens || 4096,
                temperature: args.temperature !== undefined ? args.temperature : 0.7,
            });
            const msg = completion.choices && completion.choices[0] ? completion.choices[0].message : {};
            console.log(JSON.stringify({
                success: true,
                data: {
                    content: msg.content || "",
                    role: msg.role || "assistant",
                    usage: completion.usage || {}
                }
            }));
        } else if (args.action === 'image_generate') {
            const response = await zai.images.generations.create({
                prompt: args.prompt,
                size: args.size || "1024x1024"
            });
            const imgData = response.data && response.data[0] ? response.data[0] : {};
            console.log(JSON.stringify({success: true, data: imgData}));
        } else {
            console.log(JSON.stringify({success: false, error: "Unknown action: " + args.action}));
        }
    } catch (err) {
        console.log(JSON.stringify({success: false, error: err.message}));
    }
}

main().catch(err => {
    console.log(JSON.stringify({success: false, error: err.message}));
    process.exit(0);  // Exit 0 so we can parse the error JSON
});
"""


@dataclass
class ZaiSearchResult:
    """A single search result from z-ai SDK."""
    url: str
    name: str
    snippet: str
    host_name: str
    rank: int = 0
    date: str = ""
    favicon: str = ""


@dataclass
class ZaiReaderResult:
    """Result from reading a web page via z-ai SDK."""
    title: str
    html: str
    text: str
    publish_time: str = ""
    success: bool = True
    error: str = ""


class ZaiSdkWrapper:
    """
    Python wrapper for the z-ai-web-dev-sdk Node.js module.

    Provides:
    - web_search: Search the web
    - web_reader: Extract content from web pages
    - chat: LLM chat completions

    All calls go through a Node.js subprocess that runs the SDK.

    Usage:
        wrapper = ZaiSdkWrapper()
        results = await wrapper.web_search("Python best practices", num=10)
        page = await wrapper.web_reader("https://example.com")
    """

    def __init__(self, timeout: int = 30):
        self._timeout = timeout
        self._helper_path: Optional[str] = None
        self._call_count = 0
        self._error_count = 0

    def _get_helper_path(self) -> str:
        """Get or create the helper script path."""
        if self._helper_path and os.path.exists(self._helper_path):
            return self._helper_path

        # Create a temporary helper script
        helper_dir = os.path.join(tempfile.gettempdir(), "zai_sdk_helpers")
        os.makedirs(helper_dir, exist_ok=True)
        helper_path = os.path.join(helper_dir, "zai_helper.js")

        with open(helper_path, 'w', encoding='utf-8') as f:
            f.write(_HELPER_SCRIPT)

        self._helper_path = helper_path
        return helper_path

    async def _call_node(self, args: dict) -> dict:
        """Call the Node.js helper script with the given arguments."""
        self._call_count += 1
        helper_path = self._get_helper_path()

        try:
            result = subprocess.run(
                ["node", helper_path, json.dumps(args)],
                capture_output=True,
                text=True,
                timeout=self._timeout,
                cwd=os.path.dirname(helper_path),
            )

            # Parse the output
            output = result.stdout.strip()
            if not output:
                # Try stderr for error info
                error_msg = result.stderr.strip() if result.stderr else "Empty response"
                self._error_count += 1
                return {"success": False, "error": f"Node.js helper returned empty output: {error_msg}"}

            try:
                parsed = json.loads(output)
                if not parsed.get("success", False):
                    self._error_count += 1
                return parsed
            except json.JSONDecodeError as e:
                self._error_count += 1
                return {"success": False, "error": f"JSON decode error: {e}, output: {output[:200]}"}

        except subprocess.TimeoutExpired:
            self._error_count += 1
            return {"success": False, "error": f"Node.js helper timed out after {self._timeout}s"}
        except FileNotFoundError:
            self._error_count += 1
            return {"success": False, "error": "Node.js not found — cannot use z-ai SDK"}
        except Exception as e:
            self._error_count += 1
            return {"success": False, "error": f"Unexpected error: {e}"}

    async def web_search(self, query: str, num: int = 10) -> list[ZaiSearchResult]:
        """
        Search the web using z-ai SDK.

        Args:
            query: Search query
            num: Number of results

        Returns:
            List of ZaiSearchResult objects
        """
        result = await self._call_node({
            "action": "web_search",
            "query": query,
            "num": num,
        })

        if not result.get("success", False):
            logger.warning(f"z-ai web_search failed: {result.get('error', 'unknown')}")
            return []

        data = result.get("data", [])
        search_results = []

        if isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    search_results.append(ZaiSearchResult(
                        url=item.get("url", ""),
                        name=item.get("name", ""),
                        snippet=item.get("snippet", ""),
                        host_name=item.get("host_name", ""),
                        rank=i,
                        date=item.get("date", ""),
                        favicon=item.get("favicon", ""),
                    ))

        return search_results

    async def web_reader(self, url: str) -> ZaiReaderResult:
        """
        Read a web page using z-ai SDK.

        Args:
            url: URL to read

        Returns:
            ZaiReaderResult with extracted content
        """
        result = await self._call_node({
            "action": "web_reader",
            "url": url,
        })

        if not result.get("success", False):
            error = result.get("error", "unknown error")
            logger.warning(f"z-ai web_reader failed for {url}: {error}")
            return ZaiReaderResult(
                title="",
                html="",
                text="",
                success=False,
                error=error,
            )

        data = result.get("data", {})

        if isinstance(data, dict):
            html_content = data.get("html", "") or data.get("content", "")
            title = data.get("title", "")

            # Strip HTML to get plain text
            import re
            text = re.sub(r'<[^>]+>', ' ', html_content)
            text = re.sub(r'\s+', ' ', text).strip()

            return ZaiReaderResult(
                title=title,
                html=html_content,
                text=text[:10000],  # Limit text length
                publish_time=data.get("publish_time", ""),
                success=True,
            )
        else:
            return ZaiReaderResult(
                title="",
                html="",
                text=str(data)[:5000] if data else "",
                success=bool(data),
            )

    async def chat(self, messages: list[dict], max_tokens: int = 4096,
                   temperature: float = 0.7) -> dict:
        """
        Chat completion using z-ai SDK.

        Args:
            messages: List of message dicts
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            {"success": bool, "content": str, "usage": dict, "error": str}
        """
        result = await self._call_node({
            "action": "chat",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        })

        if not result.get("success", False):
            return {"success": False, "content": "", "error": result.get("error", "unknown")}

        data = result.get("data", {})
        return {
            "success": True,
            "content": data.get("content", ""),
            "usage": data.get("usage", {}),
        }

    def get_stats(self) -> dict:
        """Get wrapper statistics."""
        return {
            "total_calls": self._call_count,
            "errors": self._error_count,
            "success_rate": (self._call_count - self._error_count) / self._call_count if self._call_count > 0 else 0.0,
            "helper_path": self._helper_path,
        }


# ── Singleton ──────────────────────────────────────────────────────────────
_zai_wrapper: Optional[ZaiSdkWrapper] = None


def get_zai_wrapper() -> ZaiSdkWrapper:
    """Get the global ZaiSdkWrapper instance."""
    global _zai_wrapper
    if _zai_wrapper is None:
        _zai_wrapper = ZaiSdkWrapper()
    return _zai_wrapper
