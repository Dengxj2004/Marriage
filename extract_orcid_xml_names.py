#!/usr/bin/env python3
"""根据 ORCID 列表从 XML 中提取 given/family name，并输出 CSV。"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import xml.etree.ElementTree as ET


NS = {
    "personal-details": "http://www.orcid.org/ns/personal-details",
}


def read_input_rows(input_csv: Path):
    """读取输入 CSV，返回 (orcid, Estimated_Change_Time) 列表。"""
    rows = []
    with input_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"ORCID", "Estimated_Change_Time"}
        if not required.issubset(reader.fieldnames or set()):
            missing = required - set(reader.fieldnames or [])
            raise ValueError(f"输入 CSV 缺少列: {', '.join(sorted(missing))}")

        for row in reader:
            orcid = (row.get("ORCID") or "").strip()
            change_time = (row.get("Estimated_Change_Time") or "").strip()
            if not orcid:
                continue
            rows.append((orcid, change_time))
    return rows


def extract_name_from_xml(xml_path: Path):
    """从 ORCID XML 中提取 given-names 与 family-name。"""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    given_node = root.find(".//personal-details:given-names", NS)
    family_node = root.find(".//personal-details:family-name", NS)

    given = (given_node.text or "").strip() if given_node is not None else ""
    family = (family_node.text or "").strip() if family_node is not None else ""
    return given, family


def main():
    parser = argparse.ArgumentParser(
        description=(
            "根据输入 CSV 的 ORCID，到 XML 目录中查找同名 XML，"
            "提取 given/family name 并输出新 CSV。"
        )
    )
    parser.add_argument("--input-csv", required=True, type=Path, help="输入 CSV 路径")
    parser.add_argument("--xml-dir", required=True, type=Path, help="XML 文件目录")
    parser.add_argument("--output-csv", required=True, type=Path, help="输出 CSV 路径")
    parser.add_argument(
        "--keep-missing",
        action="store_true",
        help="若找不到 XML 或解析失败，仍保留该 ORCID（given/family 为空）",
    )

    args = parser.parse_args()

    rows = read_input_rows(args.input_csv)
    results = []

    for orcid, change_time in rows:
        xml_path = args.xml_dir / f"{orcid}.xml"

        if not xml_path.exists():
            if args.keep_missing:
                results.append([orcid, "", "", change_time])
            else:
                print(f"[WARN] 未找到 XML: {xml_path}")
            continue

        try:
            given, family = extract_name_from_xml(xml_path)
        except ET.ParseError as e:
            if args.keep_missing:
                results.append([orcid, "", "", change_time])
            else:
                print(f"[WARN] XML 解析失败: {xml_path} ({e})")
            continue

        results.append([orcid, given, family, change_time])

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "givenname", "familyname", "Estimated_Change_Time"])
        writer.writerows(results)

    print(f"Done. 输出 {len(results)} 行 -> {args.output_csv}")


if __name__ == "__main__":
    main()
