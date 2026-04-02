"""
文件上传 API 路由

提供文件上传和解析功能。
"""
from fastapi import APIRouter, HTTPException, UploadFile
from typing import List
from pathlib import Path

from src.agents.data_parser import load_dataframe, build_dataset_meta
from src.persistence.session_store import SessionStore
from configs.settings import settings

router = APIRouter(tags=["upload"])


@router.post("/{session_id}")
async def upload_file(session_id: str, file: UploadFile):
    """
    上传文件到会话

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

    # 保存文件
    save_path = settings.UPLOAD_DIR / file.filename
    try:
        with open(save_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    # 解析文件
    df, err = load_dataframe(str(save_path))
    if df is None:
        # 清理已保存的文件
        save_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"文件解析失败: {err}")

    # 构建元信息
    meta = build_dataset_meta(df, file.filename, str(save_path))

    # 保存到数据库
    try:
        store.save_dataset(session_id, meta)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据保存失败: {str(e)}")

    return {
        "file_name": file.filename,
        "file_path": str(save_path),
        "num_rows": meta.get("num_rows"),
        "num_cols": meta.get("num_cols"),
        "columns": meta.get("columns"),
        "dtypes": meta.get("dtypes"),
        "preview": meta.get("preview"),
    }


@router.post("/{session_id}/multiple")
async def upload_multiple_files(session_id: str, files: List[UploadFile]):
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

    return results
