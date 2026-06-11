from __future__ import annotations

import shutil
import re
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.session_store import SessionStore
from app.services.data_import import (
    apply_missing_outlier_strategies,
    describe_dataframe,
    excel_sheet_names,
    load_excel_sheet,
)
from app.services.distill import train_final_model
from app.services.feature_selection import select_aux_features
from app.services.gan import gan_augment
from app.services.modeling import compare_base_models
from app.services.optimize import run_multiobjective_optimization
from app.services.screening import screen_gan_data
from app.services.teacher import train_teacher_and_pdp

router = APIRouter()
store = SessionStore()


def _json_safe(obj: Any) -> Any:
    try:
        import numpy as np
    except Exception:
        np = None  # type: ignore

    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if np is not None:
        if isinstance(obj, np.generic):
            return obj.item()
        if isinstance(obj, np.ndarray):
            return obj.tolist()
    # pandas / numpy dtypes
    try:
        import pandas as _pd

        if isinstance(obj, (_pd.Timestamp,)):
            return obj.isoformat()
    except Exception:
        pass
    return str(obj)


def _session_file_dir(session_id: str) -> Path:
    d = store.session_dir(session_id) / "files"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _read_session_dataset(session_id: str, file_name: str, sheet_name: str | None = None) -> pd.DataFrame:
    path = _session_file_dir(session_id) / file_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(path, encoding="utf-8-sig")
    elif suffix in (".xlsx", ".xls"):
        if not sheet_name:
            raise HTTPException(status_code=400, detail="sheet_name is required for Excel files")
        df = load_excel_sheet(path, sheet_name=sheet_name, header_row=0, index_col=None)
    else:
        raise HTTPException(status_code=400, detail="unsupported file type")

    df.columns = [str(c).strip() for c in df.columns]
    return df


@router.post("/sessions/{session_id}/use_sample")
def use_sample_file(session_id: str, sample_name: str = Form("All_Data.xlsx")):
    """
    Convenience endpoint for local demo: copy a workspace sample Excel into this session.
    """
    try:
        store.get(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="session not found")
    from app.core.paths import REPO_ROOT

    src = (REPO_ROOT / sample_name).resolve()
    if not src.exists():
        src = (REPO_ROOT / "data" / sample_name).resolve()
    if not src.exists():
        raise HTTPException(status_code=404, detail=f"sample not found: {sample_name}")
    dst = _session_file_dir(session_id) / Path(sample_name).name
    shutil.copyfile(src, dst)
    store.append_log(session_id, f"[sample] copied: {dst.name}")
    return {"file_name": dst.name, "sheets": excel_sheet_names(dst)}

@router.post("/sessions/{session_id}/upload")
async def upload_excel(session_id: str, file: UploadFile = File(...)):
    try:
        store.get(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="session not found")
    if not file.filename.lower().endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(status_code=400, detail="please upload an Excel or CSV file")
    dst = _session_file_dir(session_id) / file.filename
    with dst.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    store.append_log(session_id, f"[upload] saved: {dst.name}")
    if dst.suffix.lower() in (".xlsx", ".xls"):
        sheets = excel_sheet_names(dst)
    else:
        sheets = []
    return {"file_name": dst.name, "sheets": sheets, "is_excel": bool(sheets)}


@router.get("/sessions/{session_id}/files/{file_name}/sheets")
def list_sheets(session_id: str, file_name: str):
    path = _session_file_dir(session_id) / file_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    if path.suffix.lower() not in (".xlsx", ".xls"):
        return {"sheets": []}
    return {"sheets": excel_sheet_names(path)}


@router.post("/sessions/{session_id}/load_sheet")
def api_load_sheet(
    session_id: str,
    file_name: str = Form(...),
    sheet_name: str = Form(...),
    header_row: int = Form(0),
    index_col: int | None = Form(None),
):
    path = _session_file_dir(session_id) / file_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    df = load_excel_sheet(path, sheet_name=sheet_name, header_row=header_row, index_col=index_col)
    return {
        "columns": list(df.columns),
        "preview": df.head(20).to_dict(orient="records"),
        "profile": describe_dataframe(df),
    }


@router.post("/sessions/{session_id}/set_dataset")
def set_dataset(
    session_id: str,
    dataset_role: str = Form(...),  # "prior" | "exp"
    file_name: str = Form(...),
    sheet_name: str = Form(...),
    header_row: int = Form(0),
    index_col: int | None = Form(None),
    na_strategy: str = Form("keep"),
    outlier_strategy: str = Form("keep"),
):
    try:
        state = store.get(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="session not found")
    path = _session_file_dir(session_id) / file_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    df = load_excel_sheet(path, sheet_name=sheet_name, header_row=header_row, index_col=index_col)
    df2, report = apply_missing_outlier_strategies(df, na_strategy=na_strategy, outlier_strategy=outlier_strategy)
    name = "prior" if dataset_role == "prior" else "exp"
    store.write_df(session_id, name, df2)
    spec = getattr(state, name)
    spec.file_name = file_name
    spec.sheet_name = sheet_name
    spec.header_row = int(header_row)
    spec.index_col = int(index_col) if index_col is not None else None
    spec.na_strategy = na_strategy
    spec.outlier_strategy = outlier_strategy
    store.put(state)
    store.append_log(session_id, f"[data] set {name}: {file_name}::{sheet_name} rows={len(df2)} cols={df2.shape[1]}")
    return _json_safe(
        {"dataset": name, "rows": len(df2), "cols": df2.shape[1], "report": report, "profile": describe_dataframe(df2)}
    )


@router.post("/sessions/{session_id}/set_features")
def set_features(
    session_id: str,
    target: str = Form(...),
    base_features: str = Form(...),  # comma separated
    aux_features: str = Form(""),
    random_seed: int = Form(42),
):
    state = store.get(session_id)
    state.features.target = target
    state.features.base_features = [s.strip() for s in base_features.split(",") if s.strip()]
    state.features.aux_features = [s.strip() for s in aux_features.split(",") if s.strip()]
    state.models.random_seed = int(random_seed)
    store.put(state)
    return {"ok": True, "state": state.to_dict()}


@router.post("/sessions/{session_id}/step3_teacher")
def step3_teacher(session_id: str, cv_folds: int = Form(5), n_iter: int = Form(30)):
    state = store.get(session_id)
    prior = store.read_df(session_id, "prior")
    if not state.features.target or not state.features.base_features:
        raise HTTPException(status_code=400, detail="please set target and features first")
    try:
        result = train_teacher_and_pdp(
            session_id=session_id,
            store=store,
            df=prior,
            target=state.features.target,
            features=state.features.base_features,
            seed=state.models.random_seed,
            cv_folds=int(cv_folds),
            n_iter=int(n_iter),
        )
    except Exception as e:
        store.append_log(session_id, f"[step3][error] {e}")
        raise HTTPException(status_code=400, detail=str(e))
    state.models.best_teacher = result["best_model"]
    store.put(state)
    return _json_safe(result)


@router.post("/sessions/{session_id}/step4_compare_models")
def step4_compare_models(session_id: str, n_iter: int = Form(30)):
    state = store.get(session_id)
    exp = store.read_df(session_id, "exp")
    if not state.features.target or not state.features.base_features:
        raise HTTPException(status_code=400, detail="please set target and features first")
    try:
        result = compare_base_models(
            session_id=session_id,
            store=store,
            df=exp,
            target=state.features.target,
            base_features=state.features.base_features,
            aux_features=state.features.aux_features,
            seed=state.models.random_seed,
            n_iter=int(n_iter),
        )
    except Exception as e:
        store.append_log(session_id, f"[step4][error] {e}")
        raise HTTPException(status_code=400, detail=str(e))
    state.models.best_base_model = result["best_model"]
    state.models.best_feature_set = result["best_features"]
    store.put(state)
    return _json_safe(result)


@router.post("/sessions/{session_id}/step5_feature_selection")
def step5_feature_selection(session_id: str, top_k: int = Form(5)):
    state = store.get(session_id)
    exp = store.read_df(session_id, "exp")
    if not state.features.target:
        raise HTTPException(status_code=400, detail="please set target first")
    try:
        result = select_aux_features(
            session_id=session_id,
            store=store,
            df=exp,
            target=state.features.target,
            candidate_features=list(dict.fromkeys(state.features.base_features + state.features.aux_features)),
            seed=state.models.random_seed,
            top_k=int(top_k),
        )
    except Exception as e:
        store.append_log(session_id, f"[step5][error] {e}")
        raise HTTPException(status_code=400, detail=str(e))
    state.models.best_feature_set = result["selected_features"]
    store.put(state)
    return _json_safe(result)


@router.post("/sessions/{session_id}/step6_gan")
def step6_gan(
    session_id: str,
    epochs: int = Form(500),
    n_generate: int = Form(200),
    latent_dim: int = Form(32),
    batch_size: int = Form(32),
):
    state = store.get(session_id)
    exp = store.read_df(session_id, "exp")
    features = state.models.best_feature_set or (state.features.base_features + state.features.aux_features)
    if not state.features.target or not features:
        raise HTTPException(status_code=400, detail="missing target/features")
    state.gan.epochs = int(epochs)
    state.gan.n_generate = int(n_generate)
    state.gan.latent_dim = int(latent_dim)
    state.gan.batch_size = int(batch_size)
    store.put(state)
    try:
        result = gan_augment(
            session_id=session_id,
            store=store,
            df=exp,
            features=features,
            target=state.features.target,
            seed=state.models.random_seed,
            epochs=state.gan.epochs,
            latent_dim=state.gan.latent_dim,
            batch_size=state.gan.batch_size,
            n_generate=state.gan.n_generate,
        )
        return _json_safe(result)
    except Exception as e:
        store.append_log(session_id, f"[step6][error] {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/{session_id}/step7_screen")
def step7_screen(session_id: str, pred_abs_tol: float = Form(0.05), max_keep: int = Form(200)):
    state = store.get(session_id)
    exp = store.read_df(session_id, "exp")
    gan_df = store.read_df(session_id, "gan_raw")
    features = state.models.best_feature_set or (state.features.base_features + state.features.aux_features)
    state.screening.pred_abs_tol = float(pred_abs_tol)
    state.screening.max_keep = int(max_keep)
    store.put(state)
    try:
        result = screen_gan_data(
            session_id=session_id,
            store=store,
            exp_df=exp,
            gan_df=gan_df,
            features=features,
            target=state.features.target,
            seed=state.models.random_seed,
            pred_abs_tol=state.screening.pred_abs_tol,
            max_keep=state.screening.max_keep,
        )
        return _json_safe(result)
    except Exception as e:
        store.append_log(session_id, f"[step7][error] {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/{session_id}/step8_final")
def step8_final(session_id: str, alpha: float = Form(0.3), method: str = Form("soft_label")):
    state = store.get(session_id)
    prior = store.read_df(session_id, "prior")
    exp = store.read_df(session_id, "exp")
    try:
        gan_filtered = store.read_df(session_id, "gan_filtered")
    except FileNotFoundError:
        gan_filtered = pd.DataFrame()

    features = state.models.best_feature_set or (state.features.base_features + state.features.aux_features)
    state.distill.alpha = float(alpha)
    state.distill.method = method
    store.put(state)
    try:
        result = train_final_model(
            session_id=session_id,
            store=store,
            prior_df=prior,
            exp_df=exp,
            aug_df=gan_filtered,
            features=features,
            target=state.features.target,
            seed=state.models.random_seed,
            alpha=state.distill.alpha,
            method=state.distill.method,
            teacher_model_name=state.models.best_teacher,
            base_model_name=state.models.best_base_model,
        )
        return _json_safe(result)
    except Exception as e:
        store.append_log(session_id, f"[step8][error] {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/{session_id}/step9_optimize")
def step9_optimize(
    session_id: str,
    n_samples: int = Form(3000),
    objective_mode: str = Form("maximize_target_minimize_l2"),
    cost_formula: str = Form(""),
):
    state = store.get(session_id)
    state.optimize.n_samples = int(n_samples)
    state.optimize.objective_mode = objective_mode
    store.put(state)
    features = state.models.best_feature_set or (state.features.base_features + state.features.aux_features)
    try:
        result = run_multiobjective_optimization(
            session_id=session_id,
            store=store,
            features=features,
            target=state.features.target,
            seed=state.models.random_seed,
            n_samples=state.optimize.n_samples,
            objective_mode=state.optimize.objective_mode,
            cost_formula=cost_formula,
        )
        return _json_safe(result)
    except Exception as e:
        store.append_log(session_id, f"[step9][error] {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sessions/{session_id}/download/{artifact_name}")
def download_artifact(session_id: str, artifact_name: str):
    path = store.artifact_path(session_id, artifact_name)
    if not path.exists():
        # allow direct file lookup for csv/png created by services
        alt = store.session_dir(session_id) / "artifacts" / artifact_name
        if alt.exists():
            path = alt
        else:
            raise HTTPException(status_code=404, detail="artifact not found")
    return FileResponse(path)


@router.post("/sessions/{session_id}/step10_test")
async def step10_test(
    session_id: str,
    file: UploadFile | None = File(None),
    file_name: str | None = Form(None),
    sheet_name: str | None = Form(None),
):
    """
    Upload a validation/test set and evaluate:
    1. all models trained in step4
    2. the saved final/distilled model from step8, if available
    Supports CSV or Excel.
    """
    import io
    import joblib
    import numpy as np
    from app.utils.metrics import regression_metrics

    try:
        state = store.get(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="session not found")

    source_name = file_name
    if file is not None:
        raw = await file.read()
        source_name = file.filename
        if file.filename.lower().endswith(".csv"):
            test_df = pd.read_csv(io.BytesIO(raw), encoding="utf-8-sig")
        elif file.filename.lower().endswith((".xlsx", ".xls")):
            test_df = pd.read_excel(io.BytesIO(raw), sheet_name=sheet_name or 0, engine="openpyxl")
        else:
            raise HTTPException(status_code=400, detail="please upload csv/xlsx/xls")
    elif file_name:
        test_df = _read_session_dataset(session_id, file_name=file_name, sheet_name=sheet_name)
    else:
        raise HTTPException(status_code=400, detail="please provide a test file")
    test_df.columns = [str(c).strip() for c in test_df.columns]
    store.write_df(session_id, "test", test_df)

    state.notes["test_file_name"] = source_name
    state.notes["test_sheet_name"] = sheet_name
    store.put(state)

    compare_csv = store.artifact_path(session_id, "step4_model_compare.csv")
    if not compare_csv.exists():
        raise HTTPException(status_code=400, detail="step4 comparison not found; run step4 first")

    compare_df = pd.read_csv(compare_csv, encoding="utf-8-sig")
    if compare_df.empty:
        raise HTTPException(status_code=400, detail="step4 comparison is empty; run step4 first")
    if "bundle_artifact" not in compare_df.columns:
        raise HTTPException(status_code=400, detail="step4 comparison is outdated; rerun step4 to refresh model bundles")

    prediction_df = test_df.copy()
    summary_rows: list[dict[str, Any]] = []
    target_col = None

    teacher_bundle = None

    def _ensure_teacher_pred_column() -> None:
        nonlocal teacher_bundle
        if "teacher_pred" in prediction_df.columns:
            return
        teacher_path = store.artifact_path(session_id, "teacher_model.joblib")
        if not teacher_path.exists():
            raise HTTPException(status_code=400, detail="teacher_model.joblib not found (required for teacher_pred)")
        if teacher_bundle is None:
            teacher_bundle = joblib.load(teacher_path)
        teacher = teacher_bundle["model"]
        teacher_feats = teacher_bundle["features"]
        missing_teacher = [c for c in teacher_feats if c not in prediction_df.columns]
        if missing_teacher:
            raise HTTPException(status_code=400, detail=f"test set missing teacher features: {missing_teacher}")
        prediction_df["teacher_pred"] = teacher.predict(prediction_df[teacher_feats].values)

    def _append_model_result(
        *,
        model: Any,
        feats: list[str],
        row_label: dict[str, Any],
        row_target: str,
    ) -> None:
        nonlocal target_col
        target_col = row_target

        if "teacher_pred" in feats:
            _ensure_teacher_pred_column()

        missing = [c for c in feats if c not in prediction_df.columns]
        if missing:
            raise HTTPException(status_code=400, detail=f"test set missing features: {missing}")

        safe_label = re.sub(
            r"[^A-Za-z0-9_.-]+",
            "_",
            f"{row_label['feature_set']}__{row_label['model']}",
        ).strip("_")
        pred_col = f"pred__{safe_label}"
        y_pred = model.predict(prediction_df[feats].copy())
        prediction_df[pred_col] = y_pred

        metric_row: dict[str, Any] = {
            **row_label,
            "pred_col": pred_col,
            "r2": None,
            "rmse": None,
            "mae": None,
        }
        if row_target in prediction_df.columns:
            metrics = regression_metrics(prediction_df[row_target].values, y_pred)
            metric_row.update(metrics)
        summary_rows.append(metric_row)

    if compare_df["bundle_artifact"].isna().any():
        raise HTTPException(status_code=400, detail="step4 comparison is missing model bundle artifacts")

    for row in compare_df.to_dict(orient="records"):
        bundle_path = store.artifact_path(session_id, row["bundle_artifact"])
        if not bundle_path.exists():
            raise HTTPException(status_code=400, detail=f"missing saved model bundle: {row['bundle_artifact']}")
        bundle = joblib.load(bundle_path)
        _append_model_result(
            model=bundle["model"],
            feats=bundle["features"],
            row_target=bundle["target"],
            row_label={
                "feature_set": row["feature_set"],
                "model": row["model"],
                "bundle_artifact": row["bundle_artifact"],
            },
        )

    final_model_path = store.artifact_path(session_id, "final_model.joblib")
    if final_model_path.exists():
        final_bundle = joblib.load(final_model_path)
        final_method = final_bundle.get("method", "final")
        final_model_name = final_bundle.get("model_name", "FinalModel")
        _append_model_result(
            model=final_bundle["model"],
            feats=final_bundle["features"],
            row_target=final_bundle["target"],
            row_label={
                "feature_set": f"FinalModel[{final_method}]",
                "model": final_model_name,
                "bundle_artifact": final_model_path.name,
            },
        )

    summary_df = pd.DataFrame(summary_rows)
    if "r2" in summary_df.columns and summary_df["r2"].notna().any():
        summary_df = summary_df.sort_values(["r2", "rmse"], ascending=[False, True])

    out_pred = store.artifact_path(session_id, "step10_test_predictions.csv")
    out_summary = store.artifact_path(session_id, "step10_test_compare.csv")
    prediction_df.to_csv(out_pred, index=False, encoding="utf-8-sig")
    summary_df.to_csv(out_summary, index=False, encoding="utf-8-sig")

    out_png = store.artifact_path(session_id, "step10_test_compare.png")
    if target_col and target_col in prediction_df.columns:
        from app.utils.plots import save_metric_panels

        save_metric_panels(
            out_png,
            summary_df.assign(label=summary_df["feature_set"] + " / " + summary_df["model"]),
            label_col="label",
            metric_cols=["r2", "rmse"],
            title="Test Set Model Comparison",
            top_n=min(12, len(summary_df)),
            sort_by="r2",
        )

    summary_preview_df = summary_df.head(20).copy()
    if not summary_df.empty and "feature_set" in summary_df.columns:
        final_mask = summary_df["feature_set"].astype(str).str.startswith("FinalModel[")
        if final_mask.any():
            final_row_df = summary_df.loc[final_mask].head(1)
            final_pred_col = final_row_df.iloc[0].get("pred_col")
            preview_has_final = (
                "feature_set" in summary_preview_df.columns
                and summary_preview_df["feature_set"].astype(str).str.startswith("FinalModel[").any()
            )
            if not preview_has_final:
                summary_preview_df = pd.concat([summary_preview_df, final_row_df], ignore_index=True)
                if len(summary_preview_df) > 20:
                    summary_preview_df = pd.concat(
                        [summary_preview_df.head(19), final_row_df],
                        ignore_index=True,
                    )

                if final_pred_col and final_pred_col in prediction_df.columns:
                    preferred_cols = list(dict.fromkeys(
                        [target_col] + [col for col in prediction_df.columns if not str(col).startswith("pred__")] + [final_pred_col]
                    ))
                    prediction_preview_df = prediction_df[preferred_cols].head(20).copy()
                else:
                    prediction_preview_df = prediction_df.head(20).copy()
            else:
                prediction_preview_df = prediction_df.head(20).copy()
        else:
            prediction_preview_df = prediction_df.head(20).copy()
    else:
        prediction_preview_df = prediction_df.head(20).copy()

    best_row = summary_df.iloc[0].to_dict() if len(summary_df) > 0 else {}
    store.append_log(session_id, f"[step10] rows={len(prediction_df)} models={len(summary_df)}")
    return _json_safe(
        {
            "rows": int(len(prediction_df)),
            "models": int(len(summary_df)),
            "best_model": {"feature_set": best_row.get("feature_set"), "model": best_row.get("model")},
            "metrics": {k: best_row.get(k) for k in ("r2", "rmse", "mae")} if best_row else None,
            "prediction_csv_artifact": out_pred.name,
            "summary_csv_artifact": out_summary.name,
            "summary_png_artifact": out_png.name if out_png.exists() else None,
            "prediction_preview": prediction_preview_df.to_dict(orient="records"),
            "summary_preview": summary_preview_df.to_dict(orient="records"),
            "test_file_name": source_name,
            "test_sheet_name": sheet_name,
        }
    )


@router.post("/sessions/{session_id}/step11_next_iter")
def step11_next_iter(session_id: str):
    """
    Merge the last uploaded test prediction CSV (or manually provided test set)
    into Exp data and start a new iteration.
    """
    try:
        state = store.get(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="session not found")

    exp = store.read_df(session_id, "exp")
    try:
        test_df = store.read_df(session_id, "test")
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="no test dataset found; run step10 first")

    if state.features.target and state.features.target not in test_df.columns:
        raise HTTPException(status_code=400, detail="test set has no target column; cannot promote to ExpData")

    missing_exp_cols = [col for col in exp.columns if col not in test_df.columns]
    if missing_exp_cols:
        raise HTTPException(
            status_code=400,
            detail=f"test set is missing required experimental columns: {missing_exp_cols}",
        )

    merged = pd.concat([exp, test_df[exp.columns].copy()], ignore_index=True)
    store.write_df(session_id, "exp", merged)

    state.iteration = int(state.iteration) + 1
    state.exp.file_name = "generated_from_exp_plus_test.csv"
    state.exp.sheet_name = None
    store.put(state)

    store.append_log(session_id, f"[step11] iteration={state.iteration} exp_rows={len(merged)}")
    return _json_safe(
        {
            "ok": True,
            "iteration": state.iteration,
            "exp_rows": int(len(merged)),
            "exp_cols": int(merged.shape[1]),
            "added_rows": int(len(test_df)),
            "profile": describe_dataframe(merged),
        }
    )
