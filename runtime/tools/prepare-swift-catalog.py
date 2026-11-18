#!/usr/bin/env python3
"""Split the pinned Madeira catalog literal in the temporary Xcode build tree."""
import sys
from pathlib import Path

path = Path(sys.argv[1]) / "app/Madeira/ConfigCatalog.generated.swift"
text = path.read_text()
declaration = "    static let generated: [ConfigOption] = "
header, rows = text.split(declaration + "[\n", 1)
footer = "    ]\n}\n"
if not rows.endswith(footer):
    raise SystemExit("Unexpected end of generated catalog")
options = rows[:-len(footer)].splitlines()
if not options or not all(row.startswith("        ConfigOption(") and row.endswith("),") for row in options):
    raise SystemExit("Unexpected configuration option layout")

# Each function has its own type-checking budget. Keep the original row text and order.
groups = [options[i:i + 32] for i in range(0, len(options), 32)]
output = [header + declaration + "{", "        var options: [ConfigOption] = []"]
for index in range(len(groups)):
    output.append(f"        options.append(contentsOf: catalogGroup{index}())")
output.extend(["        return options", "    }()"])
for index, group in enumerate(groups):
    output.extend(["", f"    private static func catalogGroup{index}() -> [ConfigOption] {{", "        ["])
    output.extend(group)
    output.extend(["        ]", "    }"])
path.write_text("\n".join(output + ["}", ""]))
print(f"Prepared {len(options)} configuration options in {len(groups)} groups")
