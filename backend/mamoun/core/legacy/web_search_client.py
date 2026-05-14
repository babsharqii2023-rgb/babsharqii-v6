"""
BABSHARQII v21.0 — Web Search Client
عميل بحث الويب — يستخدم z-ai-web-dev-sdk أو HTTP مباشرة
"""

import os
import logging
import httpx
from typing import Optional

logger = logging.getLogger("mamoun.core.web_search_client")


async def search_web(query: str, num: int = 10) -> list:
    """
    بحث في الويب — يرجع قائمة نتائج
    
    كل نتيجة تحتوي على:
    - url: رابط الصفحة
    - name/title: عنوان الصفحة
    - snippet: مقتطف من الصفحة
    """
    results = []

    # Method 1: Try z-ai-web-dev-sdk
    try:
        import asyncio
        from pathlib import Path
        
        # Check if SDK is available
        sdk_path = Path(__file__).parent.parent.parent.parent / "node_modules" / "z-ai-web-dev-sdk"
        if sdk_path.exists():
            proc = await asyncio.create_subprocess_exec(
                "node", "-e",
                f"""
                const ZAI = require('z-ai-web-dev-sdk');
                async function main() {{
                    const zai = await ZAI.create();
                    const result = await zai.functions.invoke("web_search", {{
                        query: {repr(query)},
                        num: {num}
                    }});
                    console.log(JSON.stringify(result));
                }}
                main().catch(e => console.error(e.message));
                """,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
            if proc.returncode == 0 and stdout:
                data = json.loads(stdout.decode())
                if isinstance(data, list):
                    for item in data:
                        results.append({
                            "url": item.get("url", ""),
                            "name": item.get("name", ""),
                            "title": item.get("name", ""),
                            "snippet": item.get("snippet", ""),
                        })
                    return results
    except Exception as e:
        logger.debug("z-ai SDK search failed: %s", e)

    # Method 2: DuckDuckGo HTML (no API key needed)
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            if resp.status_code == 200:
                import re
                # Parse results from HTML
                pattern = r'<a rel="nofollow" class="result__a" href="([^"]+)">(.*?)</a>'
                snippets = re.findall(
                    r'<a class="result__snippet".*?>(.*?)</a>',
                    resp.text, re.DOTALL
                )
                links = re.findall(pattern, resp.text, re.DOTALL)
                
                for i, (url, title) in enumerate(links[:num]):
                    clean_title = re.sub(r'<[^>]+>', '', title).strip()
                    clean_snippet = ""
                    if i < len(snippets):
                        clean_snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()
                    
                    results.append({
                        "url": url,
                        "name": clean_title,
                        "title": clean_title,
                        "snippet": clean_snippet[:300],
                    })
    except Exception as e:
        logger.warning("DuckDuckGo search error: %s", e)

    # No fake data — if all real search methods failed, return empty with a clear message
    if not results:
        logger.info("No real search results found for query: %s — refusing to generate fake data", query)
        return [{
            "url": "",
            "name": "لا توجد نتائج حقيقية",
            "title": "لم أجد نتائج حقيقية — لا أريد تضليلك ببيانات مزيفة",
            "snippet": f"لم أجد نتائج حقيقية للبحث عن: {query}. يُرجى المحاولة بصياغة مختلفة أو لاحقاً.",
        }]

    return results


import json
