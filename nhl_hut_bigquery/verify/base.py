from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CheckResult:
    name: str
    violations: int
    total: int
    passed: bool

    def summary(self) -> str:
        return (
            f"{self.name}: {self.violations}/{self.total} violations — "
            f"{'PASS' if self.passed else 'FAIL'}"
        )


@dataclass
class VerifyResult:
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def overall_pass(self) -> bool:
        return all(c.passed for c in self.checks)

    def summary(self) -> str:
        return "\n".join(c.summary() for c in self.checks)
