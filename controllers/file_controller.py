import logging
import re
import uuid
from pathlib import Path

from flask import Blueprint, abort, current_app, jsonify, request, send_file
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename

from database import get_session
from Models import Car, CarImage, SecureFile, User


logger = logging.getLogger(__name__)
file_bp = Blueprint("files", __name__, url_prefix="/api")
IMAGE_MIMES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
DOCUMENT_MIMES = {**IMAGE_MIMES, "application/pdf": ".pdf"}
DOCUMENT_KINDS = {"ownership", "seller_id", "import_duty"}
DOCUMENT_LABELS = {
    "ownership": "Proof of ownership / title / logbook",
    "seller_id": "Seller National ID",
    "import_duty": "Import / duty verification",
}
IMAGE_LABELS = {
    "vehicle_photo_front": "Front vehicle photo",
    "vehicle_photo_side": "Side vehicle photo",
    "vehicle_photo_rear": "Rear vehicle photo",
}


def _storage_root():
    return Path(current_app.config["PRIVATE_UPLOAD_FOLDER"]).resolve()


def _save_upload(upload, allowed_types, kind, owner_id, car_id=None):
    if not upload or not upload.filename:
        raise ValueError(f"A file is required for {kind}.")
    media_type = (upload.mimetype or "").lower()
    extension = allowed_types.get(media_type)
    if not extension:
        raise ValueError("Choose a PDF, JPG, PNG, or WebP file as allowed for this upload.")
    storage_name = f"{uuid.uuid4().hex}{extension}"
    target = _storage_root() / storage_name
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        upload.save(target)
        size = target.stat().st_size
        if size <= 0 or size > current_app.config["MAX_CONTENT_LENGTH"]:
            raise ValueError("File is empty or larger than the permitted upload size.")
        file_record = SecureFile(
            owner_id=owner_id,
            car_id=car_id,
            kind=kind,
            original_name=secure_filename(upload.filename)[:255] or f"{kind}{extension}",
            storage_name=storage_name,
            media_type=media_type,
            size_bytes=size,
        )
        return file_record, target
    except Exception:
        target.unlink(missing_ok=True)
        raise


def _remove_saved_files(paths):
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.exception("Unable to remove an uncommitted private upload.")


@file_bp.route("/cars/<int:car_id>/photos", methods=["POST"])
@jwt_required()
def upload_vehicle_photos(car_id):
    db = get_session()
    try:
        car = db.get(Car, car_id)
        if not car:
            return jsonify({"error": "Vehicle not found."}), 404
        user_id = int(get_jwt_identity())
        role = get_jwt().get("role")
        if car.seller_id != user_id and role != "admin":
            return jsonify({"error": "Only the listing owner can upload vehicle photos."}), 403
        records = []
        saved_paths = []
        try:
            for kind, upload in IMAGE_LABELS.items():
                upload = request.files.get(kind)
                if not upload or not upload.filename:
                    continue
                record, path = _save_upload(upload, IMAGE_MIMES, kind, car.seller_id, car.id)
                records.append(record)
                saved_paths.append(path)
            if not records:
                return jsonify({"error": "Select at least one vehicle photo."}), 400
            existing_image_count = db.query(CarImage).filter(CarImage.car_id == car.id).count()
            db.add_all(records)
            db.flush()
            for index, record in enumerate(records):
                db.add(CarImage(
                    car_id=car.id,
                    image_url=f"/api/public/vehicle-photos/{record.storage_name}",
                    is_primary=(existing_image_count == 0 and index == 0),
                ))
            db.commit()
            db.refresh(car)
            from schemas import car_schema
            return jsonify(car_schema.dump(car)), 201
        except ValueError as error:
            db.rollback()
            _remove_saved_files(saved_paths)
            return jsonify({"error": str(error)}), 400
        except Exception:
            db.rollback()
            _remove_saved_files(saved_paths)
            logger.exception("Vehicle photo upload failed.")
            return jsonify({"error": "Vehicle photos could not be saved."}), 500
    finally:
        db.close()


@file_bp.route("/private-documents", methods=["POST"])
@jwt_required()
def upload_private_documents():
    if get_jwt().get("role") != "seller":
        return jsonify({"error": "Only sellers can upload their own legal documents."}), 403
    user_id = int(get_jwt_identity())
    car_id = request.form.get("car_id", type=int)
    online_sale = request.form.get("online_sale", "").lower() == "true"
    if not car_id or not online_sale:
        return jsonify({"error": "A vehicle and online-sale consent are required."}), 400
    db = get_session()
    try:
        car = db.get(Car, car_id)
        if not car or car.seller_id != user_id:
            return jsonify({"error": "The vehicle listing was not found for this seller."}), 404
        if not car.online_sale:
            return jsonify({"error": "The vehicle listing must be marked for online sale."}), 400
        finance_status = request.form.get("finance_status", "")
        imported_value = request.form.get("imported_vehicle")
        online_sale_consent = request.form.get("online_sale_consent") == "true"
        ecitizen_phone = re.sub(r"[\s().-]", "", request.form.get("ecitizen_phone", ""))
        seller = db.get(User, user_id)
        identity_file = request.files.get("seller_id")
        if not seller or not seller.national_id:
            return jsonify({"error": "Seller National ID must be saved before submitting documents."}), 400
        if not identity_file or not identity_file.filename:
            return jsonify({"error": "Seller National ID document is required."}), 400
        if not online_sale_consent:
            return jsonify({"error": "Confirm the ownership and legal-status information to continue."}), 400
        if finance_status not in {"clear", "active-finance", "active-lease"}:
            return jsonify({"error": "Select the vehicle title, finance, or lease status."}), 400
        if imported_value not in {"true", "false"}:
            return jsonify({"error": "Specify whether the vehicle was imported."}), 400
        if not re.fullmatch(r"\+[1-9]\d{7,14}", ecitizen_phone):
            return jsonify({"error": "Provide the registered eCitizen phone number in international format."}), 400
        required_kinds = ["ownership", "seller_id"]
        if imported_value == "true":
            required_kinds.append("import_duty")
        for kind in IMAGE_LABELS:
            if not request.files.get(kind) or not request.files[kind].filename:
                return jsonify({"error": "Upload all three vehicle photos with the required legal documents."}), 400
        records = []
        saved_paths = []
        try:
            for kind in required_kinds:
                record, path = _save_upload(
                    request.files.get(kind),
                    DOCUMENT_MIMES,
                    kind,
                    user_id,
                    car_id,
                )
                records.append(record)
                saved_paths.append(path)
            for kind, label in IMAGE_LABELS.items():
                upload = request.files.get(kind)
                if upload and upload.filename:
                    record, path = _save_upload(upload, IMAGE_MIMES, kind, user_id, car_id)
                    records.append(record)
                    saved_paths.append(path)
            existing_image_count = db.query(CarImage).filter(CarImage.car_id == car_id).count()
            db.add_all(records)
            db.flush()
            for record in (item for item in records if item.kind in IMAGE_LABELS):
                db.add(CarImage(
                    car_id=car_id,
                    image_url=f"/api/public/vehicle-photos/{record.storage_name}",
                    is_primary=(existing_image_count == 0 and record.kind == "vehicle_photo_front"),
                ))
            car.finance_status = finance_status
            car.imported_vehicle = imported_value == "true"
            seller_phone = seller.phone_number if seller else ""
            if ecitizen_phone != seller_phone:
                raise ValueError("Registered eCitizen phone must match the verified seller phone.")
            db.commit()
            return jsonify({"message": "Required legal documents securely stored."}), 201
        except ValueError as error:
            db.rollback()
            _remove_saved_files(saved_paths)
            return jsonify({"error": str(error)}), 400
        except Exception:
            db.rollback()
            _remove_saved_files(saved_paths)
            logger.exception("Private legal document upload failed.")
            return jsonify({"error": "Legal documents could not be securely stored."}), 500
    finally:
        db.close()


@file_bp.route("/public/vehicle-photos/<storage_name>", methods=["GET"])
def get_public_vehicle_photo(storage_name):
    if not re.fullmatch(r"[0-9a-f]{32}\.(jpg|png|webp)", storage_name):
        abort(404)
    db = get_session()
    try:
        record = (
            db.query(SecureFile)
            .join(Car, SecureFile.car_id == Car.id)
            .filter(
                SecureFile.storage_name == storage_name,
                SecureFile.kind.in_(IMAGE_LABELS),
                Car.status == "active",
            )
            .first()
        )
        if not record:
            abort(404)
        path = (_storage_root() / record.storage_name).resolve()
        if path.parent != _storage_root() or not path.is_file():
            abort(404)
        return send_file(path, mimetype=record.media_type, conditional=True, max_age=300)
    finally:
        db.close()


@file_bp.route("/admin/documents", methods=["GET"])
@jwt_required()
def list_private_documents():
    if get_jwt().get("role") != "admin":
        return jsonify({"error": "Only administrators can view seller documents."}), 403
    db = get_session()
    try:
        records = (
            db.query(SecureFile)
            .options(joinedload(SecureFile.owner), joinedload(SecureFile.car))
            .filter(SecureFile.kind.in_(DOCUMENT_KINDS))
            .order_by(SecureFile.created_at.desc())
            .all()
        )
        return jsonify([{
            "id": record.id,
            "kind": record.kind,
            "label": DOCUMENT_LABELS[record.kind],
            "original_name": record.original_name,
            "media_type": record.media_type,
            "size_bytes": record.size_bytes,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "seller_name": record.owner.full_name if record.owner else "",
            "seller_email": record.owner.email if record.owner else "",
            "car_id": record.car_id,
            "vehicle": f"{record.car.make} {record.car.model}" if record.car else "Vehicle removed",
            "file_url": f"/api/admin/documents/{record.id}/content",
        } for record in records]), 200
    finally:
        db.close()


@file_bp.route("/admin/documents/<int:file_id>/content", methods=["GET"])
@jwt_required()
def get_private_document(file_id):
    if get_jwt().get("role") != "admin":
        return jsonify({"error": "Only administrators can view seller documents."}), 403
    db = get_session()
    try:
        record = db.get(SecureFile, file_id)
        if not record or record.kind not in DOCUMENT_KINDS:
            abort(404)
        path = (_storage_root() / record.storage_name).resolve()
        if path.parent != _storage_root() or not path.is_file():
            abort(404)
        return send_file(
            path,
            mimetype=record.media_type,
            as_attachment=True,
            download_name=record.original_name,
            conditional=True,
            max_age=0,
        )
    finally:
        db.close()


@file_bp.route("/cars/<int:car_id>/photos/<int:image_id>", methods=["DELETE"])
@jwt_required()
def delete_vehicle_photo(car_id, image_id):
    db = get_session()
    try:
        car = db.get(Car, car_id)
        image = db.get(CarImage, image_id)
        if not car or not image or image.car_id != car_id:
            return jsonify({"error": "Vehicle image not found."}), 404
        role = get_jwt().get("role")
        if car.seller_id != int(get_jwt_identity()) and role != "admin":
            return jsonify({"error": "Only the listing owner can remove vehicle photos."}), 403
        record = db.query(SecureFile).filter(
            SecureFile.car_id == car_id,
            SecureFile.kind.in_(IMAGE_LABELS),
            SecureFile.storage_name == image.image_url.rsplit("/", 1)[-1],
        ).first()
        db.delete(image)
        if record:
            path = (_storage_root() / record.storage_name).resolve()
            db.delete(record)
            db.commit()
            if path.parent == _storage_root():
                path.unlink(missing_ok=True)
        else:
            db.commit()
        return "", 204
    except Exception:
        db.rollback()
        logger.exception("Vehicle photo removal failed.")
        return jsonify({"error": "Vehicle photo could not be removed."}), 500
    finally:
        db.close()
