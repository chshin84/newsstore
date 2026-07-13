import ast
import pathlib

SRC = pathlib.Path("src/newsstore")
# 각 모듈이 import하면 안 되는 형제 모듈 prefix (오직 contracts에만 의존해야 함)
FORBIDDEN = {
    "collect": ("newsstore.store",),
    "store":   ("newsstore.collect",),
}


def _imported_modules(py: pathlib.Path):
    """절대(newsstore.x)·상대(..x) import를 모두 절대 dotted 경로로 정규화해 yield."""
    tree = ast.parse(py.read_text(encoding="utf-8"))
    pkg_parts = py.relative_to(SRC.parent).with_suffix("").parts  # ('newsstore','store','x')
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            if n.level:                       # 상대 import → 절대화
                base = pkg_parts[: len(pkg_parts) - n.level]
                mod = ".".join(base + ((n.module,) if n.module else ()))
            else:
                mod = n.module or ""
            yield mod
        elif isinstance(n, ast.Import):
            for a in n.names:
                yield a.name


def test_modules_only_depend_on_contracts():
    violations = []
    for mod, banned in FORBIDDEN.items():
        for py in (SRC / mod).rglob("*.py"):
            for imp in _imported_modules(py):
                if imp.startswith(banned):
                    violations.append(f"{py}  imports  {imp}")
    assert not violations, (
        "모듈 경계 위반(collect/store는 서로 import 금지, contracts만):\n"
        + "\n".join(violations)
    )
