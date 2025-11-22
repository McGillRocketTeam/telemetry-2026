import pandas as pd
import re
from pathlib import Path
from typing import Dict, List
import os

# -------------------- Parsing --------------------

def load_encoding_types(file_path: str, sheet_name: str = "Encoding Types") -> dict:
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    df.columns = df.columns.str.strip().str.lower()

    encoding_dict = dict(zip(df["name"], df["c++ type"]))

    # Return C++ type strings directly from Excel
    return {
        name: c_type
        for name, c_type in encoding_dict.items()
        if c_type
    }

def load_atomics(file_path: str, sheet_name: str = "Atomics") -> dict:
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    df.columns = df.columns.astype(str).str.strip()

    atomics_to_params = {}
    for col in df.columns:
        if col.lower().startswith(("name", "parameter")):
            continue
        vals = (
            df[col]
            .dropna()
            .astype(str)
            .str.strip()
            .tolist()
        )
        vals = [v for v in vals if v]
        vals = list(dict.fromkeys(vals))
        atomics_to_params[col] = vals
    return atomics_to_params

def load_parameters(file_path: str, sheet_name: str = "Parameters") -> dict:
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=1)
    df.columns = df.columns.astype(str).str.strip().str.lower()

    if "variable name" not in df.columns or "encoding" not in df.columns:
        raise ValueError("Sheet must contain 'Variable Name' and 'Encoding' columns.")

    return dict(zip(df["variable name"].str.strip(), df["encoding"].str.strip()))

# -------------------- Helpers --------------------

def to_identifier(s: str) -> str:
    s = re.sub(r"\W", "_", s)
    if re.match(r"^\d", s):
        s = "_" + s
    return s


def check_cwd():
    EXPECTED_DIR = "parser"
    cwd = Path(os.getcwd()).resolve()
    if cwd.name != EXPECTED_DIR:
        raise RuntimeError(
            f"[Error] Please run this script from inside the '{EXPECTED_DIR}' folder.\n"
            f"Current directory: {cwd}\n"
            f"Try:\n  cd {EXPECTED_DIR}\n  python parse_excel.py"
        )

# -------------------- Section builders --------------------

def build_preamble() -> str:
    lines = [
        "// AUTO-GENERATED. Do not edit by hand.",
        "#pragma once"
        "",
        "#ifdef __cplusplus",
        "#include <cstdint>",
    ]
    lines.append("")  # blank line
    return "\n".join(lines)

def build_postamble() -> str:
    return "#endif"

def build_atomic_enum_section(atomics_to_params: Dict[str, List[str]]) -> str:
    lines = []
    lines.append("// ---------- AtomicType Enum ----------")
    lines.append("enum AtomicType {")
    for i, atomic in enumerate(atomics_to_params.keys()):
        lines.append(f"    AT_{to_identifier(atomic).upper():<20} = {i},  // bit {i}")
    lines.append("    AT_TOTAL                             // total count")
    lines.append("};\n")
    return "\n".join(lines)

def build_single_atomic_section(
    atomic_name: str,
    params: List[str],
    param_to_cpp_type
) -> str:
    struct_name   = to_identifier(atomic_name)
    data_typedef  = f"{struct_name}_data"
    union_typedef = f"{struct_name}_packet"

    lines = []
    lines.append(f"// ---------- {struct_name} atomic ----------")
    lines.append(f"typedef struct __attribute__((__packed__)) {data_typedef}")
    lines.append("{")
    for p in params:
        field = to_identifier(p)
        cpp_type = param_to_cpp_type.get(p)
        if cpp_type:
            if cpp_type == "bool":
                lines.append(f"    bool {field} : 1;")  # 1 bit for bool
            elif cpp_type == "char[6]":
                lines.append(f"    char {field}[6];")
            else:
                lines.append(f"    {cpp_type} {field};")
        else:
            lines.append(f"    // TODO: Missing encoding for {field}")
    lines.append(f"}} {data_typedef};\n")
    lines.append(f"typedef union {union_typedef} {{")
    lines.append(f"    {data_typedef} data;")
    lines.append(f"    uint8_t bytes[sizeof({data_typedef})];")
    lines.append(f"}} {union_typedef};\n")
    return "\n".join(lines)

def build_atomics_section(
    atomics_to_params: Dict[str, List[str]],
    param_to_cpp_type
) -> str:
    parts = []
    for atomic, params in atomics_to_params.items():
        parts.append(
            build_single_atomic_section(
                atomic, params, param_to_cpp_type
                )
        )
    return "\n".join(parts)

def build_atomic_size_declaration() -> str:
    return "\n".join([
        "// ---------- Atomic Size Catalog (declaration) ----------",
        "extern const uint16_t AT_SIZE[AT_TOTAL];",
        ""
    ])

def build_atomic_size_definition_cpp(atomics_to_params: Dict[str, List[str]], header_basename: str) -> str:
    lines = []
    lines.append("// AUTO-GENERATED. Do not edit by hand.")
    lines.append(f'#include "{header_basename}"')
    lines.append("")
    lines.append("// ---------- Atomic Size Catalog (definition) ----------")
    lines.append("const uint16_t AT_SIZE[AT_TOTAL] = {")
    for i, atomic in enumerate(atomics_to_params.keys()):
        struct_name = to_identifier(atomic)
        lines.append(f"    /*{i}*/ sizeof({struct_name}_data),")
    lines.append("};\n")
    return "\n".join(lines)

def build_packet_printer(atomics_to_params: Dict[str, List[str]]) -> str:
    lines = []

    # Packet printer header
    lines.append("// AUTO-GENERATED. Do not edit by hand.")
    lines.append("#include \"frame_printer.h\"")
    lines.append("#include <Arduino.h>")
    lines.append("")

    # Define the macro for printing fields
    lines.append("#define PRINT_FIELD(p, field) { \\")
    lines.append("  Serial.print(F(#field \": \")); \\")
    lines.append("  Serial.println(p->field); \\")
    lines.append("}")
    lines.append("")

    # Function to print bool values in a human-readable format
    lines.append("static inline void printBoolLine(const __FlashStringHelper* label, bool b) {")
    lines.append("  Serial.print(label);")
    lines.append("  Serial.println(b ? F(\"true\") : F(\"false\"));")
    lines.append("}")
    lines.append("")

    # Atomic type names
    lines.append("const __FlashStringHelper* atomicTypeName(AtomicType at) {")
    lines.append("  switch (at) {")
    for i, atomic in enumerate(atomics_to_params.keys()):
        lines.append(f"    case AT_{to_identifier(atomic).upper()}: return F(\"{atomic}\");")
    lines.append("    default: return F(\"unknown_atomic\");")
    lines.append("  }")
    lines.append("}")
    lines.append("")

    # Print functions for each atomic type (add more if needed)
    for atomic, params in atomics_to_params.items():
        struct_name = to_identifier(atomic)
        lines.append(f"// ---------------- {atomic} ----------------")
        lines.append(f"void print{struct_name.capitalize()}Atomic(const {struct_name}_data* p) {{")
        lines.append("  if (!p) return;")
        lines.append(f"  Serial.println(F(\"{atomic} {{\"));")
        for param in params:
            field = to_identifier(param)
            lines.append(f"  PRINT_FIELD(p, {field});")
        lines.append(f"  Serial.println(F(\"}}\"));")
        lines.append("}")
        lines.append("")

    # Atomic dispatcher function
    lines.append("void printAtomic(const FrameView& view, AtomicType at) {")
    lines.append("  switch (at) {")
    for i, atomic in enumerate(atomics_to_params.keys()):
        struct_name = to_identifier(atomic)
        lines.append(f"    case AT_{to_identifier(atomic).upper()}: {{")
        lines.append(f"      const auto* p = view.atomicAs<{struct_name}_data>(AT_{to_identifier(atomic).upper()});")
        lines.append(f"      print{struct_name.capitalize()}Atomic(p);")
        lines.append("      break;")
        lines.append("    }")
    lines.append("    default: Serial.print(F(\"Unknown atomic type: \")); Serial.println(static_cast<int>(at)); break;")
    lines.append("  }")
    lines.append("}")
    lines.append("")

    # Print all atomics
    lines.append("void printAtomics(const FrameView& view) {")
    lines.append("  Serial.println(F(\"\\n--- Atomics (decoded) ---\"));")
    lines.append("  for (int i = 0; i < AT_TOTAL; ++i) {")
    lines.append("    auto at = static_cast<AtomicType>(i);")
    lines.append("    if (view.hasAtomic(at)) {")
    lines.append("      printAtomic(view, at);")
    lines.append("    }")
    lines.append("  }")
    lines.append("}")
    
    return "\n".join(lines)


# -------------------- Emitters --------------------

def generate_telemetry_packets(
    out_base: str,
    atomics_to_params: Dict[str, List[str]],
    param_to_cpp_type
) -> None:
    
    out_header = Path(out_base).with_suffix(".h")
    out_cpp    = Path(out_base).with_suffix(".cpp")

    header_sections = [
        build_preamble(),
        build_atomic_enum_section(atomics_to_params),
        build_atomics_section(atomics_to_params, param_to_cpp_type),
        build_atomic_size_declaration(),
        build_postamble(),
    ]
    out_header.write_text("\n".join(header_sections), encoding="utf-8")

    cpp_body = build_atomic_size_definition_cpp(
        atomics_to_params,
        header_basename=out_header.name
    )
    out_cpp.write_text(cpp_body, encoding="utf-8")

    print(f"Wrote {out_header}")
    print(f"Wrote {out_cpp}")
    

def generate_telemetry_printer(
    out_base: str,
    atomics_to_params: Dict[str, List[str]]
) -> None:
    
    packet_printer_cpp = Path(out_base).with_suffix(".cpp")
    packet_printer_body = build_packet_printer(atomics_to_params)
    packet_printer_cpp.write_text(packet_printer_body, encoding="utf-8")

    print(f"Wrote {packet_printer_cpp}")


if __name__ == "__main__":
    FILE = "https://docs.google.com/spreadsheets/d/1Ukaums3NfbJdVOQL7E1QMyPNoQ7gD5Zxciiz4ucRUrk/export?format=xlsx"
    check_cwd()

    encoding_to_cpp_type = load_encoding_types(FILE)
    param_to_encoding = load_parameters(FILE)
    atomics_to_params = load_atomics(FILE)

    param_to_cpp_type = {
        param: encoding_to_cpp_type.get(encoding)
        for param, encoding in param_to_encoding.items()
        if encoding in encoding_to_cpp_type
    }

    generate_telemetry_packets(
        out_base="../telemetry/gen/telemetry_packets",
        atomics_to_params=atomics_to_params,
        param_to_cpp_type=param_to_cpp_type
    )
    
    generate_telemetry_printer(
        out_base="../telemetry/gen/frame_printer",
        atomics_to_params=atomics_to_params
    )
    
