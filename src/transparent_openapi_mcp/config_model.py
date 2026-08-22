"""Config data model.

Implements the config schema from architecture.md:
- SpecEntry pairs one OpenAPI spec URL with its own tool-name prefix
  and its own paired backend base URL (R-CFG-001).
- Config is a named bundle of one or more SpecEntry (R-CFG-001,
  R-CFG-002), with an optional config-level default timeout
  (R-CFG-006).
- ConfigList holds the full set of configs plus a MANDATORY
  server-wide default timeout (R-CFG-007) and an optional
  preselected config name (R-BOOT-001).
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

_CAMEL_CASE_JSON = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class SpecEntry(BaseModel):
    """One OpenAPI spec source paired with its backend target.

    R-CFG-001: prefix, spec_url, and backend_base_url are all
    required. timeout_seconds is optional (R-CFG-005) and falls back
    through Config.default_timeout_seconds and
    ConfigList.default_timeout_seconds when absent (R-FWD-002).

    R-CFG-003: JSON keys are camelCase (specUrl, backendBaseUrl,
    timeoutSeconds), matching Claude Code's MCP config conventions.
    Python attribute access stays snake_case either way
    (populate_by_name=True).
    """

    model_config = _CAMEL_CASE_JSON

    prefix: str
    spec_url: str
    backend_base_url: str
    timeout_seconds: int | None = None


class Config(BaseModel):
    """A named bundle of one or more spec entries (R-CFG-001/002)."""

    model_config = _CAMEL_CASE_JSON

    name: str
    specs: list[SpecEntry] = Field(min_length=1)
    default_timeout_seconds: int | None = None


class ConfigList(BaseModel):
    """The full config list loaded from the config-list URL.

    R-CFG-007: default_timeout_seconds is mandatory here - there is
    no hardcoded last-resort value, so a config list missing this
    field fails validation.
    R-BOOT-001: preselected optionally names a Config to select at
    startup.
    """

    model_config = _CAMEL_CASE_JSON

    configs: list[Config]
    default_timeout_seconds: int
    preselected: str | None = None

    def effective_timeout_seconds(self, entry: SpecEntry) -> int:
        """Resolve R-FWD-002's fallback chain for one spec entry.

        Order: the entry's own timeout, else the owning config's
        default, else this list's mandatory default. The caller is
        responsible for passing an entry that belongs to one of this
        list's configs; this method does not search for the owner.
        """
        if entry.timeout_seconds is not None:
            return entry.timeout_seconds
        owning_config = self._find_owning_config(entry)
        if owning_config is not None and owning_config.default_timeout_seconds is not None:
            return owning_config.default_timeout_seconds
        return self.default_timeout_seconds

    def _find_owning_config(self, entry: SpecEntry) -> Config | None:
        for config in self.configs:
            if entry in config.specs:
                return config
        return None
