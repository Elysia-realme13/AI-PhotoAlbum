"""
模型管理 API 路由

提供训练完成后的模型管理接口：列表、详情、导出、导入、删除、设为默认
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import get_required_user
from app.models.user import User
from app.services import training_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/models", tags=["模型管理"])


@router.get("")
def list_models(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """获取所有训练完成的模型列表"""
    try:
        models = training_service.get_models(db)
        return {"total": len(models), "items": models}
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取模型列表失败: {str(e)}")


@router.get("/{model_name}")
def get_model_detail(
    model_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """获取模型详情（含训练指标数据）"""
    try:
        detail = training_service.get_model_detail(model_name, db)
        if "error" in detail:
            raise HTTPException(status_code=404, detail=detail["error"])
        return detail
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模型详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



@router.patch("/{model_name}")
def update_model(
    model_name: str,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """更新模型的任务名称和描述"""
    task_name = data.get("task_name")
    description = data.get("description")
    if not task_name or not task_name.strip():
        raise HTTPException(status_code=400, detail="任务名称不能为空")
    result = training_service.update_model(model_name, task_name.strip(), description, db)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{model_name}/export")
def export_model(
    model_name: str,
    format: str = Form("pt"),
    current_user: User = Depends(get_required_user),
):
    """导出模型文件（支持 pt / onnx 格式）"""
    if format not in ("pt", "onnx"):
        raise HTTPException(status_code=400, detail="不支持的导出格式，仅支持 pt / onnx")

    file_path = training_service.export_model(model_name, format)
    if not file_path:
        raise HTTPException(status_code=404, detail="模型文件不存在，请先完成训练")

    return FileResponse(
        path=file_path,
        filename=f"{model_name}.{format}",
        media_type="application/octet-stream",
    )


@router.post("/import")
def import_model(
    file: UploadFile = File(...),
    model_name: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """导入已有的模型文件（.pt / .pth / .onnx）"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="请选择要导入的文件")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("pt", "pth", "onnx"):
        raise HTTPException(status_code=400, detail="不支持的模型格式，仅支持 .pt / .pth / .onnx")

    try:
        file_bytes = file.file.read()
        training_service.import_model(file_bytes, file.filename, model_name, db)
        return {"message": f"模型 {model_name} 导入成功", "model_name": model_name}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"导入模型失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.post("/{model_name}/set-default")
def set_default_model(
    model_name: str,
    current_user: User = Depends(get_required_user),
):
    """设置当前使用的检测模型"""
    success = training_service.set_default_model(model_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"模型 '{model_name}' 不存在")
    return {"message": f"默认模型已设置为 {model_name}", "model_name": model_name}


@router.get("/default/info")
def get_default_model():
    """获取当前默认模型信息"""
    try:
        from app.services.training_service import _get_default_model
        model_name = _get_default_model()
        if model_name:
            return {"model_name": model_name}
        return {"model_name": None, "message": "未设置默认模型，系统将使用 YOLO 预训练模型"}
    except Exception as e:
        logger.error(f"获取默认模型失败: {e}", exc_info=True)
        return {"model_name": None, "message": str(e)}


@router.post("/default/reset")
def reset_default_model(
    current_user: User = Depends(get_required_user),
):
    """将默认模型重置为 YOLOv26"""
    try:
        training_service.reset_default_model()
        return {"message": "已重置为 YOLOv26 预训练模型", "model_name": None}
    except Exception as e:
        logger.error(f"重置默认模型失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{model_name}")
def delete_model(
    model_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """删除模型"""
    success = training_service.delete_model(model_name, db)
    if not success:
        raise HTTPException(status_code=404, detail="模型不存在")
    return {"message": f"模型 '{model_name}' 已删除"}
