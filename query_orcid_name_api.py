#!/usr/bin/env python3
"""读取姓名 CSV，填充 Prompt 并逐条调用聊天 API。"""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Any
from urllib import request, error

# ================= 配置区域 =================
API_KEY = "sk-3PutokDpcdfTDskKwt8lwlKct56ufggkcPxReCamYhbM2igw"
API_URL = "https://yinli.one/v1/chat/completions"
MODEL = "gemini-3-pro-preview"

PROMPT_TEMPLATE = """You are an expert in Onomastics (the study of names), Cultural Anthropology, and Demography.
Your task is to probabilistically infer the cultural origin of a specific female scholar based on her personal name, and to assess the traditional marital surname change practices of that culture.

You must adhere to the following constraints at all times:
- All inferences must be probabilistic, not definitive.
- If a name is culturally ambiguous, explicitly acknowledge multiple plausible origins.
- Your assessment concerns traditional or normative naming customs, not individual modern choices.
- Avoid overconfidence or stereotyping; uncertainty should be clearly stated when applicable.

Input Data
Given Name: {{GIVEN_NAME}}
Family Name: {{FAMILY_NAME}}

Task Logic:
1.Analyze Name Synergy
Analyze the combination of the Given Name and Family Name to infer the most likely cultural origin(s) or ethnicity.

Guidelines:
- Prioritize cultural/ethnic origin over current country of residence.
- Use the full name to resolve ambiguity where possible.
- If multiple cultural origins are plausible, list them explicitly.

2.Determine Traditional Marital Naming Practice
Based on the inferred cultural origin(s), assess whether that culture traditionally practices marital surname change (i.e., women replacing their birth surname with their husband’s surname).

3.Classification
Assign one of the following values:
YES: Cultures where replacing their birth surname with their husband’s surname is the traditional norm (e.g., Anglo, Germanic, Slavic/Russian, French).

NO: Cultures where women traditionally retain their birth surname after marriage (e.g., Chinese, Korean, Vietnamese, Iranian, Arab/Islamic, Italian).

COMPLEX: Cultures with legally optional, socially diverse, or structurally non-binary surname systems, including but not limited to:
- Double surnames (e.g., Hispanic/Lusophone)
- Naming systems with high ambiguity (e.g., "Lee" could be English or Korean).
- Cultures where the practice is legally optional and socially 50/50 (e.g., Modern Dutch).

4.Confidence Assessment
Provide a qualitative confidence level for your inference:
- HIGH: Strong, unambiguous cultural signals
- MEDIUM: Some ambiguity but dominant likelihood
- LOW: High ambiguity or multiple equally plausible cultural interpretations

Few-Shot Examples
Example 1 (Clear Case)
Input:
Given Name: "Mary"
Family Name: "Smith"

Output:
{
"inferred_origin": "Anglo/Western",
"practices_marital_name_change": "YES",
"confidence_level": "HIGH",
"reasoning": "Both given name and surname are strongly associated with Anglo-Saxon cultures, where marital surname replacement has been the traditional norm."
}
"""


def build_prompt(given_name: str, family_name: str) -> str:
    return (
        PROMPT_TEMPLATE.replace("{{GIVEN_NAME}}", given_name or "")
        .replace("{{FAMILY_NAME}}", family_name or "")
    )


def call_chat_api(prompt: str, timeout: int = 90) -> dict[str, Any]:
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }

    req = request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
        method="POST",
    )

    with request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def extract_answer(api_json: dict[str, Any]) -> str:
    try:
        return api_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return json.dumps(api_json, ensure_ascii=False)


def iter_rows(input_csv: Path):
    with input_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


def main() -> None:
    parser = argparse.ArgumentParser(description="读取 CSV 并逐条调用 API，打印每条回复")
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path("/hy-tmp/Marriage所有相关文件/New_Marriage/extract_orcid_names.csv"),
        help="输入 CSV 路径（应含 id/givenname/familyname）",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("api_name_inference_results.csv"),
        help="输出 CSV（保存原字段 + API 回复）",
    )
    parser.add_argument("--sleep", type=float, default=0.5, help="每次请求后等待秒数")
    parser.add_argument("--max-rows", type=int, default=0, help="仅处理前 N 条，0=全部")
    args = parser.parse_args()

    rows = list(iter_rows(args.input_csv))
    if args.max_rows > 0:
        rows = rows[: args.max_rows]

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)

    out_fields = ["id", "givenname", "familyname", "Estimated_Change_Time", "api_reply", "api_error"]

    with args.output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()

        for idx, row in enumerate(rows, start=1):
            record_id = (row.get("id") or "").strip()
            givenname = (row.get("givenname") or "").strip()
            familyname = (row.get("familyname") or "").strip()
            change_time = (row.get("Estimated_Change_Time") or "").strip()

            prompt = build_prompt(givenname, familyname)

            api_reply = ""
            api_error = ""
            try:
                resp_json = call_chat_api(prompt)
                api_reply = extract_answer(resp_json)
            except error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                api_error = f"HTTPError {e.code}: {err_body}"
            except error.URLError as e:
                api_error = f"URLError: {e.reason}"
            except Exception as e:
                api_error = f"Exception: {e}"

            print("=" * 80)
            print(f"[{idx}] id={record_id} | givenname={givenname} | familyname={familyname}")
            if api_error:
                print(f"[ERROR] {api_error}")
            else:
                print("[API_REPLY]")
                print(api_reply)

            writer.writerow(
                {
                    "id": record_id,
                    "givenname": givenname,
                    "familyname": familyname,
                    "Estimated_Change_Time": change_time,
                    "api_reply": api_reply,
                    "api_error": api_error,
                }
            )

            if args.sleep > 0:
                time.sleep(args.sleep)

    print(f"\nDone. 已保存结果到: {args.output_csv}")


if __name__ == "__main__":
    main()
