import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Literal

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from analytics import build_insight_context, build_summary
from chat_data import execute_query_spec
from data_loader import (
    MAX_UPLOAD_BYTES,
    get_sales_data_snapshot,
    install_uploaded_dataset,
    load_sales_data,
    reset_to_default_dataset,
    validate_uploaded_csv,
)
from ml.forecasting import clear_forecast_cache, get_cached_forecast

load_dotenv(Path(__file__).resolve().parent / ".env")
logger = logging.getLogger(__name__)
app = FastAPI(title="Sales AI API")
allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    history: list[ChatMessage] = Field(default_factory=list, max_length=8)


def _sales_data() -> pd.DataFrame:
    try:
        return load_sales_data()
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Sales data is unavailable: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _sales_snapshot() -> tuple[pd.DataFrame, str]:
    try:
        return get_sales_data_snapshot()
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Sales data is unavailable: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _gemini_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="AI features are unavailable. Configure GEMINI_API_KEY in backend/.env.",
        )
    return genai.Client(api_key=api_key)


def _json_response(client: genai.Client, prompt: str) -> dict:
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )
        except Exception as exc:
            status = getattr(exc, "code", None)
            retryable = status is None or status == 429 or (isinstance(status, int) and status >= 500)
            if attempt == 0 and retryable:
                logger.warning("Gemini request failed; retrying once")
                time.sleep(0.5)
                continue
            logger.exception("Gemini request failed")
            detail = (
                "The AI service is rate-limited. Please try again shortly."
                if status == 429
                else "The AI service is temporarily unavailable. Please try again."
            )
            raise HTTPException(status_code=503, detail=detail) from exc
        try:
            parsed = json.loads(response.text or "")
            if not isinstance(parsed, dict):
                raise json.JSONDecodeError("Expected a JSON object", response.text or "", 0)
            return parsed
        except (json.JSONDecodeError, TypeError):
            if attempt == 1:
                raise HTTPException(
                    status_code=502,
                    detail="The AI service returned an invalid response. Please try again.",
                )
            prompt += "\nReturn valid JSON only, matching the requested object exactly."
    raise HTTPException(status_code=502, detail="The AI service could not return valid JSON.")


def _text_response(client: genai.Client, prompt: str) -> str:
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.2),
            )
            return (response.text or "").strip()
        except Exception as exc:
            status = getattr(exc, "code", None)
            retryable = status is None or status == 429 or (isinstance(status, int) and status >= 500)
            if attempt == 0 and retryable:
                logger.warning("Gemini response generation failed; retrying once")
                time.sleep(0.5)
                continue
            logger.exception("Gemini response generation failed")
            detail = (
                "The AI service is rate-limited. Please try again shortly."
                if status == 429
                else "The AI service is temporarily unavailable. Please try again."
            )
            raise HTTPException(status_code=503, detail=detail) from exc
    raise HTTPException(status_code=503, detail="The AI service is temporarily unavailable.")


@app.get("/")
def read_root():
    return {"message": "AI Backend Active", "status": 200}


@app.get("/api/forecast")
def get_forecast(horizon: int = Query(default=3, ge=1, le=6)):
    df, version = _sales_snapshot()
    try:
        result = get_cached_forecast(df, version)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "history": result.history,
        "forecast": result.forecast[:horizon],
        "model": result.model,
    }


@app.get("/api/model-metrics")
def get_model_metrics():
    df, version = _sales_snapshot()
    try:
        result = get_cached_forecast(df, version)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"selectedModel": result.model, "metrics": result.metrics}


@app.get("/api/summary")
def get_summary():
    try:
        return build_summary(_sales_data())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/insights")
def get_insights():
    df, version = _sales_snapshot()
    try:
        forecast = get_cached_forecast(df, version)
        context = build_insight_context(df, forecast)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    narrative = (
        "Recent revenue is moving in line with the selected forecasting model. "
        "Review the latest monthly trend and any flagged periods before adjusting plans."
    )
    recommendation = (
        "Review the next forecast alongside recent inventory and campaign plans before committing changes."
    )
    if os.getenv("GEMINI_API_KEY"):
        prompt = (
            "You are a sales analyst. Narrate only the provided calculated context. "
            "Return JSON with exactly two string keys: narrative (two or three short sentences) "
            "and recommendation (exactly one practical action). Do not add any numbers, dates, "
            "percentages, or factual claims not explicitly present in the context. "
            f"Calculated context: {json.dumps(context, ensure_ascii=True)}"
        )
        generated = _json_response(_gemini_client(), prompt)
        if not isinstance(generated.get("narrative"), str) or not isinstance(
            generated.get("recommendation"), str
        ):
            raise HTTPException(status_code=502, detail="The AI service returned malformed insights.")
        if re.search(r"\d", generated["narrative"] + generated["recommendation"]):
            logger.warning("Discarded Gemini insights with uncomputed numeric claims")
        else:
            narrative = generated["narrative"]
            recommendation = generated["recommendation"]
    return {"metrics": context, "narrative": narrative, "recommendation": recommendation}


@app.post("/api/upload")
async def upload_sales_csv(file: UploadFile = File(...)):
    if not file.filename or Path(file.filename).suffix.lower() != ".csv":
        raise HTTPException(status_code=400, detail="Choose a file with a .csv extension.")
    try:
        contents = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(contents) > MAX_UPLOAD_BYTES:
            raise ValueError(f"CSV exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB upload limit.")
        frame = validate_uploaded_csv(contents)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await file.close()

    version = install_uploaded_dataset(frame)
    clear_forecast_cache()
    return {
        "message": "CSV validated and loaded for this session.",
        "rows": len(frame),
        "datasetVersion": version,
    }


@app.post("/api/upload/reset")
def reset_sales_csv():
    reset_to_default_dataset()
    clear_forecast_cache()
    frame, version = _sales_snapshot()
    return {
        "message": "Restored the bundled default dataset.",
        "rows": len(frame),
        "datasetVersion": version,
    }


@app.post("/api/chat")
def post_chat(request: ChatRequest):
    df = _sales_data()
    client = _gemini_client()
    sample = df.head(3).copy()
    sample["Date"] = sample["Date"].dt.strftime("%Y-%m-%d")
    schema = {
        "columns": {column: str(dtype) for column, dtype in df.dtypes.items()},
        "sample_rows": sample.to_dict(orient="records"),
    }
    history = [
        {"role": item.role, "content": item.content}
        for item in request.history[-6:]
    ]
    plan_prompt = (
        "Plan a read-only analysis of a retail sales dataframe. Never write code or SQL. "
        "Use only query_spec fields: group_by (up to two of day, month, year, Product, Category, Region), "
        "metric (Revenue or Units), filters (Product/Category/Region arrays or ISO date_from/date_to), "
        "sort_by, sort_order (asc/desc), and limit (1-50). "
        "Return JSON with intent (answerable or unsupported), query_spec, chart_type (line/bar/area/pie/none), "
        "x_key, y_keys, and title. Mark unsupported when the data cannot answer the question. "
        f"Schema and sample: {json.dumps(schema, ensure_ascii=True)}\n"
        f"Recent conversation: {json.dumps(history, ensure_ascii=True)}\n"
        f"Question: {request.message}"
    )
    plan = _json_response(client, plan_prompt)
    if not isinstance(plan, dict):
        raise HTTPException(status_code=502, detail="The AI service returned an invalid query plan.")
    if plan.get("intent") != "answerable":
        return {
            "message": "I can only answer questions supported by the sales data (dates, products, categories, regions, units, and revenue).",
            "response_type": "text",
            "chart": None,
            "rows": [],
        }

    query_spec = plan.get("query_spec")
    try:
        result = execute_query_spec(df, query_spec)
    except (ValueError, TypeError) as exc:
        logger.info("Rejected invalid AI query plan: %s", exc)
        raise HTTPException(
            status_code=422,
            detail="I couldn't safely interpret that data request. Try a product, region, category, or date-based question.",
        ) from exc

    rows = result["data"]
    chart_types = {"line", "bar", "area", "pie"}
    chart = None
    response_type = "table"
    if rows and plan.get("chart_type") in chart_types and result["y_keys"]:
        chart = {
            "type": plan["chart_type"],
            "title": str(plan.get("title") or f"{result['metric']} by {result['x_key']}")[:100],
            "x_key": result["x_key"],
            "y_keys": result["y_keys"],
            "data": rows,
        }
        response_type = "chart"

    answer_prompt = (
        "Answer the user briefly using only the computed results below. Do not infer missing data "
        "or introduce numbers not present in the results. Do not use any digits; exact values are "
        "already visible in the chart or table. If there are no rows, say no matching data "
        "was found. Do not mention implementation details.\n"
        f"Question: {request.message}\n"
        f"Computed results: {json.dumps(rows[:50], ensure_ascii=True)}"
    )
    message = _text_response(client, answer_prompt)
    if not message or re.search(r"\d", message):
        message = "I couldn't produce a summary for those results. Please try rephrasing the question."
    return {"message": message, "response_type": response_type, "chart": chart, "rows": rows[:50]}
