from __future__ import annotations
import asyncio
import inspect
import logging
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)


class Kernel:
    """Lightweight plugin kernel with async invoke."""

    def __init__(self) -> None:
        self._plugins: Dict[str, Any] = {}

    def register_plugin(self, name: str, plugin: Any) -> None:
        """Register a plugin and inject the kernel into it, if supported."""
        # Give the plugin a handle to the kernel, one of:
        # - constructor got it already
        # - attribute `kernel`
        # - setter `set_kernel(...)`
        try:
            if getattr(plugin, "kernel", None) is None:
                if hasattr(plugin, "set_kernel") and callable(plugin.set_kernel):
                    plugin.set_kernel(self)
                elif hasattr(plugin, "__dict__"):
                    setattr(plugin, "kernel", self)
        except Exception as e:
            log.warning("[Kernel] Could not inject kernel into '%s': %s", name, e)

        self._plugins[name] = plugin
        log.info("[Kernel] Registered plugin '%s' from %s", name, plugin.__class__.__name__)

    def get_plugin(self, name: str) -> Any:
        if name not in self._plugins:
            raise RuntimeError(f"Plugin '{name}' not loaded")
        return self._plugins[name]

    async def invoke_function(self, plugin_name: str, method: str, args: Optional[Dict[str, Any]] = None) -> Any:
        """Invoke a plugin method; supports sync and async functions."""
        plugin = self.get_plugin(plugin_name)
        if not hasattr(plugin, method):
            raise AttributeError(f"{plugin_name}.{method} not found")
        fn = getattr(plugin, method)
        args = args or {}

        try:
            # If function is async
            if inspect.iscoroutinefunction(fn):
                return await fn(**args)
            # If function returns a coroutine (factory style)
            result = fn(**args)
            if inspect.isawaitable(result):
                return await result
            # Synchronous result
            return result
        except Exception as e:
            log.exception("[Kernel] invoke %s.%s failed: %s", plugin_name, method, e)
            raise


async def _make_plugin(k: Kernel, cls_path: str, name: str) -> None:
    """
    Dynamically import a plugin and register it.
    Tries ctor with kernel, falls back to no-arg then kernel injection.
    """
    mod_path, cls_name = cls_path.rsplit(".", 1)
    try:
        module = __import__(mod_path, fromlist=[cls_name])
        cls = getattr(module, cls_name)
        try:
            # Prefer ctor(kernel)
            instance = cls(k)
        except TypeError:
            # Fallback to no-arg
            instance = cls()
        k.register_plugin(name, instance)
    except Exception as e:
        log.error("[Kernel] Failed to register '%s' (%s): %s", name, cls_path, e)


async def build_kernel() -> Kernel:
    """
    Build the kernel and register all plugins we need.
    Keep going even if one plugin fails.
    """
    k = Kernel()

    # Core plugins
    await _make_plugin(k, "src.plugins.ocr_plugin.OCRPlugin",           "ocr")
    await _make_plugin(k, "src.plugins.policy_plugin.PolicyPlugin",     "policy")
    await _make_plugin(k, "src.plugins.translate_plugin.TranslatePlugin","translate")

    # RAG & crawl (citations / KB population)
    await _make_plugin(k, "src.plugins.rag_plugin.RAGPlugin",           "rag")
    await _make_plugin(k, "src.plugins.crawl_plugin.CrawlPlugin",       "crawl")

    return k
