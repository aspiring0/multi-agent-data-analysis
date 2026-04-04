"""
文件上传 API 路由

提供文件上传和解析功能。
文件存储到数据库（小文件）或文件系统（大文件）。
"""
from __future__ import annotations

import io
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from src.agents.data_parser import load_dataframe, build_dataset_meta
from src.persistence.session_store import SessionStore
from src.storage.file_store import get_file_store
from configs.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["upload"])


@router.post("/{session_id}")
async def upload_file(session_id: str, file: UploadFile):
    """
    上传文件到会话

    文件存储到数据库（小文件 < 1MB）或文件系统（大文件）。

    Args:
        session_id: 会话 ID
        file: 上传的文件

    Returns:
        dict: 文件元信息
    """
    # 验证会话存在
    store = SessionStore()
    if not store.get_session(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")

    # 验证文件类型
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in [".csv", ".tsv", ".xlsx", ".xls", ".json"]:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_ext}"
        )

    # 读取文件内容
    content = await file.read()

    # 存储到数据库/文件系统
    file_store = get_file_store()
    file_id = file_store.store_file(
        session_id=session_id,
        filename=file.filename,
        content=content,
    )

    logger.info(f"File uploaded: {file.filename} ({len(content)} bytes) -> {file_id}")

    # 解析文件
    df, err = load_dataframe_from_bytes(content, file.filename)
    if df is None:
        raise HTTPException(status_code=400, detail=f"文件解析失败: {err}")

    # 构建元信息
    meta = build_dataset_meta(df, file.filename, f"db://{file_id}")
    meta["file_storage_id"] = file_id  # 添加文件存储 ID
    meta["storage_type"] = "database" if len(content) < 1024 * 1024 else "filesystem"

    # 保存到数据库
    try:
        store.save_dataset(session_id, meta)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据保存失败: {str(e)}")

    return {
        "file_id": file_id,
        "file_name": file.filename,
        "num_rows": meta.get("num_rows"),
        "num_cols": meta.get("num_cols"),
        "columns": meta.get("columns"),
        "dtypes": meta.get("dtypes"),
        "preview": meta.get("preview"),
        "storage_type": meta.get("storage_type"),
    }


@router.post("/{session_id}/multiple")
async def upload_multiple_files(session_id: str, files: list[UploadFile]):
    """
    批量上传文件

    Args:
        session_id: 会话 ID
        files: 上传的文件列表

    Returns:
        list: 所有文件的元信息
    """
    # 验证会话存在
    store = SessionStore()
    if not store.get_session(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")

    results = []

    for file in files:
        try:
            # 上传单个文件
            result = await upload_file(session_id, file)
            results.append({
                "file_name": file.filename,
                "success": True,
                **result
            })
        except HTTPException as e:
            results.append({
                "file_name": file.filename,
                "success": False,
                "error": str(e.detail)
            })

    # === 多文件关联发现 ===
    # 如果成功上传了多个文件，自动分析表间关系
    successful_uploads = [r for r in results if r.get("success")]
    if len(successful_uploads) >= 2:
        try:
            from src.storage.relationship_discovery import get_relationship_discovery

            # 获取所有数据集
            datasets = store.get_datasets(session_id)
            if datasets:
                discovery = get_relationship_discovery()
                relations = discovery.discover_relations(session_id, datasets)
                logger.info(f"发现 {len(relations)} 个表间关系")

                # 将关系信息附加到返回结果
                for r in results:
                    r["relations_discovered"] = len(relations)
        except Exception as e:
            logger.warning(f"关系发现失败: {e}")

    return results


def load_dataframe_from_bytes(content: bytes, filename: str):
    """
    从字节数据加载 DataFrame

    Args:
        content: 文件内容 (bytes)
        filename: 文件名（用于判断格式）

    Returns:
        (DataFrame, None) 成功
        (None, error_msg) 失败
    """
    import pandas as pd

    ext = Path(filename).suffix.lower()

    try:
        if ext == ".csv":
            # 尝试多种编码
            for encoding in ["utf-8-sig", "utf-8", "gbk", "latin-1"]:
                try:
                    df = pd.read_csv(io.BytesIO(content), encoding=encoding)
                    return df, None
                except UnicodeDecodeError:
                    continue
            return None, "无法解析文件编码"

        elif ext == ".tsv":
            for encoding in ["utf-8-sig", "utf-8", "gbk", "latin-1"]:
                try:
                    df = pd.read_csv(io.BytesIO(content), sep="\t", encoding=encoding)
                    return df, None
                except UnicodeDecodeError:
                    continue
            return None, "无法解析文件编码"

        elif ext in [".xlsx", ".xls"]:
            df = pd.read_excel(io.BytesIO(content))
            return df, None

        elif ext == ".json":
            df = pd.read_json(io.BytesIO(content))
            return df, None

        else:
            return None, f"不支持的文件格式: {ext}"

    except Exception as e:
        return None, str(e)
