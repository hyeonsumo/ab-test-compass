import json
import re
from pathlib import Path


CONFIG_FILE = Path("data") / "config.json"
MODEL_NAME = "gemini-flash-latest"

SYSTEM_PROMPT = """
You are an A/B testing experiment design assistant for a Korean product team.
Return only valid JSON. Do not wrap the JSON in markdown.

Schema:
{
  "name": "short experiment name in Korean",
  "hypothesis": "structured hypothesis in Korean",
  "variant_a": "control description",
  "variant_b": "treatment description",
  "primary_metric": "main metric",
  "baseline_rate": 0.10,
  "treatment_effect": 0.05,
  "variant_a_ratio": 0.5,
  "duration_days": 14,
  "risk_notes": ["risk or caveat 1", "risk or caveat 2"]
}

Rules:
- baseline_rate, treatment_effect, and variant_a_ratio must be numbers between 0 and 1.
- treatment_effect is relative lift. Example: 0.05 means +5%.
- duration_days must be an integer, at least 7 unless the user explicitly asks for a shorter demo.
- Include practical Korean A/B testing cautions: hypothesis clarity, peeking, SRM, weekday effects.
"""


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(config: dict):
    CONFIG_FILE.parent.mkdir(exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def save_api_key(api_key: str):
    config = load_config()
    config["gemini_api_key"] = api_key
    save_config(config)


def get_api_key() -> str:
    return load_config().get("gemini_api_key", "")


def design_experiment(user_prompt: str) -> dict:
    """Use Gemini to convert a natural-language idea into an experiment design."""
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("Gemini API 키가 저장되어 있지 않습니다.")

    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise RuntimeError(
            "google-generativeai 패키지가 설치되어 있지 않습니다. "
            "터미널에서 pip install google-generativeai 를 실행하세요."
        ) from exc

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        MODEL_NAME,
        system_instruction=SYSTEM_PROMPT,
    )

    response = model.generate_content(
        "다음 아이디어를 A/B 테스트 설계 JSON으로 변환해줘:\n\n"
        f"{user_prompt}"
    )
    text = getattr(response, "text", "").strip()
    text = _strip_markdown_json(text)

    try:
        result = json.loads(text)
    except json.JSONDecodeError as e:
        print("=" * 50)
        print("AI 원본 응답:")
        print(text)
        print("=" * 50)
        raise RuntimeError(f"AI 응답 파싱 실패: {e}\n\n원본: {text[:300]}") from e

    return _normalize_design(result)


def _strip_markdown_json(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1].strip()

    return text


def _normalize_design(result: dict) -> dict:
    defaults = {
        "name": "AI 설계 실험",
        "hypothesis": "",
        "variant_a": "기존안",
        "variant_b": "변경안",
        "primary_metric": "전환율",
        "baseline_rate": 0.10,
        "treatment_effect": 0.05,
        "variant_a_ratio": 0.5,
        "duration_days": 14,
        "risk_notes": [],
    }
    normalized = {**defaults, **(result or {})}

    normalized["baseline_rate"] = _clamp_float(normalized["baseline_rate"], 0.001, 0.999)
    normalized["treatment_effect"] = _clamp_float(normalized["treatment_effect"], 0.001, 1.0)
    normalized["variant_a_ratio"] = _clamp_float(normalized["variant_a_ratio"], 0.001, 0.999)
    normalized["duration_days"] = max(1, int(float(normalized["duration_days"] or 14)))

    if not isinstance(normalized["risk_notes"], list):
        normalized["risk_notes"] = [str(normalized["risk_notes"])]

    return normalized


def _clamp_float(value, low, high):
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = low
    return max(low, min(high, number))


def is_first_run() -> bool:
    """config.json이 아예 없으면 첫 실행"""
    return not CONFIG_FILE.exists()


def mark_setup_done():
    """건너뛰기를 눌렀을 때도 호출 — 다음부터는 환영 화면 안 뜨게"""
    CONFIG_FILE.parent.mkdir(exist_ok=True)
    config = load_config()
    config["setup_done"] = True
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def is_setup_done() -> bool:
    return load_config().get("setup_done", False)
