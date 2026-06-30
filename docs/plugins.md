# Detector plugins

Extend Tabayyan with your own detectors without forking the core. A detector
is any subclass of `tabayyan.detectors.base.Detector` that yields `Match`
objects — and it inherits the same [contract tests](https://github.com/nasser-gh/Tabayyan/blob/main/tests/test_contracts.py)
the built-ins are held to (valid spans, enum types, determinism).

## 1. Write a detector

```python
from tabayyan.detectors.base import Detector
from tabayyan.entities import Category, Confidence, EntityType, Match

class EmployeeIdDetector(Detector):
    name = "employee_id"

    def detect(self, text):
        import re
        for m in re.finditer(r"EMP-\d{6}", text):
            yield Match(EntityType.CUSTOM, Category.PERSON, Confidence.MEDIUM,
                        m.start(), m.end(), m.group(0), self.name, label="employee_id")
```

## 2a. Register it explicitly

```python
from tabayyan import register_detector, scan

register_detector(EmployeeIdDetector())     # instance
# or as a decorator on the class:
# @register_detector
# class EmployeeIdDetector(Detector): ...

scan("ticket for EMP-001234")               # now finds the custom entity
```

Registered detectors are automatically included by `DetectionEngine()` (the
default set). Passing `DetectionEngine(detectors=[...])` explicitly bypasses
the registry.

## 2b. Ship it as a package (entry-point discovery)

A third-party distribution advertises detectors under the
`tabayyan.detectors` entry-point group:

```toml
# pyproject.toml of your plugin package
[project.entry-points."tabayyan.detectors"]
employee_id = "my_plugin:EmployeeIdDetector"
```

Consumers then opt in:

```python
from tabayyan import discover_plugins
discover_plugins()      # loads + registers every advertised detector
```

> **Discovery is opt-in by design.** Because Tabayyan processes sensitive
> text, it does **not** auto-execute third-party detector code on import.
> `discover_plugins()` runs it only when you ask — treat installed plugins as
> code you trust.

## Testing your detector

Point the contract tests at your detector to get the same guarantees:

```python
from tabayyan.entities import Category, Confidence, EntityType, Match
# assert valid spans, enum types, determinism, no crash on arbitrary Unicode
```
