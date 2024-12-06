from fastapi.responses import RedirectResponse
from app.core import cloudinary
from fastapi import File, UploadFile, HTTPException
from fastapi import APIRouter, Request
from app.models.file import File as FileModel
from bson import ObjectId

router = APIRouter(prefix="/file", tags=["File"])


@router.post("")
async def upload_file(request: Request, file: UploadFile = File(...)):
    try:
        id = str(ObjectId())
        url = cloudinary.upload(file.file, public_id=id)

        new_file = FileModel(
            id=id,
            url=url,
        )
        await new_file.save()
        new_file.url = f"{request.base_url}api/file/{id}"

        return new_file.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{file_id}")
async def get_file(file_id: str):
    try:
        file = await FileModel.get(file_id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        return RedirectResponse(url=file.url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{file_id}")
async def delete_file(file_id: str):
    try:
        file = await FileModel.get(file_id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        cloudinary.delete(file_id)
        await file.delete()
        return {"detail": "File deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
