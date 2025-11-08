import pandas as pd
import ctypes

import re
from pathlib import Path
from typing import Dict, List

import os
from pathlib import Path

# Parsing

def load_encoding_types(file_path: str, sheet_name: str = "Encoding Types") -> dict:
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    df.columns = df.columns.str.strip().str.lower()

    encoding_dict = dict(zip(df["name"], df["c++ type"]))

    type_map = {
        "uint8_t": ctypes.c_ubyte,
        "uint16_t": ctypes.c_uint16,
        "uint32_t": ctypes.c_uint32,
        "int8_t": ctypes.c_byte,
        "int16_t": ctypes.c_int16,
        "int32_t": ctypes.c_int32,
        "float": ctypes.c_float,
        "double": ctypes.c_double,
        "bool": ctypes.c_bool,
        "char": ctypes.c_char,
    }

    return {
        name: type_map[c_type]
        for name, c_type in encoding_dict.items()
        if c_type in type_map
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

# Helpers for creating output

def to_pascal(s: str) -> str:
    return "".join(part.capitalize() for part in re.split(r"[_\W]+", s) if part)

def to_identifier(s: str) -> str:
    # make a valid C++ identifier (very simple sanitizer)
    s = re.sub(r"\W", "_", s)
    if re.match(r"^\d", s):
        s = "_" + s
    return s

def guard_from_path(out_path: str) -> str:
    fname = Path(out_path).name.upper()
    guard = re.sub(r"[^A-Z0-9]+", "_", fname)
    if not guard.endswith("_"):
        guard += ""
    return guard

def check_cwd():
    EXPECTED_DIR = "parser"
    cwd = Path(os.getcwd()).resolve()
    if cwd.name != EXPECTED_DIR:
        raise RuntimeError(
            f"[Error] Please run this script from inside the '{EXPECTED_DIR}' folder.\n"
            f"Current directory: {cwd}\n"
            f"Try:\n  cd {EXPECTED_DIR}\n  python parse_excel.py"
        )

# Section builders

def build_preamble(guard: str) -> str:
    return "\n".join([
        "// AUTO-GENERATED. Do not edit by hand.",
        f"#ifndef {guard}",
        f"#define {guard}",
        "",
        "#include <cstdint>",
        "",
    ])


def build_atomic_enum_section(atomics_to_params: Dict[str, List[str]]) -> str:
    lines = []
    lines.append("// ---------- AtomicType Enum ----------")
    lines.append("enum AtomicType {")
    for i, atomic in enumerate(atomics_to_params.keys()):
        lines.append(f"    AT_{to_identifier(atomic).upper():<20} = {i},  // bit {i}")
    lines.append("    AT_TOTAL                             // total count")
    lines.append("};")
    lines.append("")
    return "\n".join(lines)

def build_single_atomic_section(
    atomic_name: str,
    params: List[str],
    param_to_encoding: Dict[str, str],
    embed_header_in_atomics: bool
) -> str:
    struct_name   = to_identifier(atomic_name)
    data_typedef  = f"{struct_name}_data"
    union_typedef = f"{struct_name}_packet"

    lines = []
    lines.append(f"// ---------- {struct_name} atomic ----------")
    lines.append(f"typedef struct __attribute__((__packed__)) {data_typedef}")
    lines.append("{")

    CTYPES_TO_CPP = {
        ctypes.c_ubyte:  "uint8_t",
        ctypes.c_uint16: "uint16_t",
        ctypes.c_uint32: "uint32_t",
        ctypes.c_byte:   "int8_t",
        ctypes.c_int16:  "int16_t",
        ctypes.c_int32:  "int32_t",
        ctypes.c_float:  "float",
        ctypes.c_double: "double",
        ctypes.c_bool:   "bool",
        ctypes.c_char:   "char",
    }

    if embed_header_in_atomics:
        lines.append("    FrameHeader header;  // optional embedded header")
    for p in params:
        field = to_identifier(p)
        enc = param_to_ctype.get(p)           # you already reference this
        if enc:
            cpp_type = CTYPES_TO_CPP.get(enc)
            if cpp_type:
                lines.append(f"    {cpp_type} {field};")
            else:
                lines.append(f"    // TODO: Unmapped ctypes for {field}")
        else:
            lines.append(f"    // TODO: Missing encoding for {field}")
    lines.append(f"}} {data_typedef};")
    lines.append("")
    lines.append(f"typedef union {union_typedef} {{")
    lines.append(f"    {data_typedef} data;")
    lines.append(f"    uint8_t bytes[sizeof({data_typedef})];")
    lines.append(f"}} {union_typedef};")
    lines.append("")
    return "\n".join(lines)

def build_atomics_section(
    atomics_to_params: Dict[str, List[str]],
    param_to_encoding: Dict[str, str],
    embed_header_in_atomics: bool
) -> str:
    parts = []
    for atomic, params in atomics_to_params.items():
        parts.append(
            build_single_atomic_section(
                atomic, params, param_to_encoding, embed_header_in_atomics
            )
        )
    return "\n".join(parts)

def build_atomic_size_array_section(atomics_to_params: dict[str, list[str]]) -> str:
    """Generate static AT_SIZE[] table matching enum order."""
    lines = []
    lines.append("// ---------- Atomic Size Catalog ----------")
    lines.append("static const uint16_t AT_SIZE[AT_TOTAL] = {")
    for i, atomic in enumerate(atomics_to_params.keys()):
        struct_name = to_identifier(atomic)
        lines.append(f"    /*{i}*/ sizeof({struct_name}_data),")
    lines.append("};\n")
    return "\n".join(lines)

def build_epilogue(guard: str) -> str:
    return f"#endif // {guard}\n"


def generate_cpp_structs_packed(
    out_path: str,
    atomics_to_params: Dict[str, List[str]],
    param_to_encoding: Dict[str, str],
    embed_header_in_atomics: bool = False,
) -> None:
    guard = guard_from_path(out_path).replace(".", "_")
    sections = [
        build_preamble(guard),
        build_atomic_enum_section(atomics_to_params),
        build_atomics_section(atomics_to_params, param_to_encoding, embed_header_in_atomics),
        build_atomic_size_array_section(atomics_to_params),
        build_epilogue(guard),
    ]
    Path(out_path).write_text("\n".join(sections), encoding="utf-8")
    print(f"Wrote {out_path}")



if __name__ == "__main__":
    FILE = "telemetry.xlsx"
    check_cwd()

    ctype_dict = load_encoding_types(FILE)
    param_to_encoding = load_parameters(FILE)
    atomics_to_params = load_atomics(FILE)

    # Map each parameter to its ctype (via encoding)
    param_to_ctype = {
        param: ctype_dict.get(encoding)
        for param, encoding in param_to_encoding.items()
        if encoding in ctype_dict
    }

    # Combine with atomics
    atomics_to_fields = {
        atomic: [(p, param_to_ctype.get(p)) for p in params]
        for atomic, params in atomics_to_params.items()
    }
    # print("Ctype dict\n", ctype_dict)
    # print("Param to encoding:\n", param_to_encoding)
    # print("Param to cytpe:\n", param_to_ctype)
    # print("Atomics to fields:\n", atomics_to_fields)


    generate_cpp_structs_packed(
        out_path="../telemetry/gen/telemetry_packets.h",
        atomics_to_params=atomics_to_params,
        param_to_encoding=param_to_encoding
        )

