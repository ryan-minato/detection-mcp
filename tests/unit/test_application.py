import json
from pathlib import Path

import pytest
from filelock import FileLock

from detection_mcp.errors import DomainError, ErrorCode
from detection_mcp.models import AnnotationType, BBoxCreate, CategoryCreate, ExportMode, ImageStatus, RotatedBBoxCreate
from detection_mcp.services.application import Application

pytestmark = pytest.mark.unit


def _dataset_and_category(application: Application, image_root: Path) -> tuple[int, int]:
    dataset = application.create_dataset(str(image_root), "sample")
    categories = application.add_categories(
        dataset["dataset_id"],
        [CategoryCreate(name="vehicle", description="A road vehicle")],
    )
    return dataset["dataset_id"], categories["categories"][0]["category_id"]


def test_dataset_soft_delete_and_restore(application: Application, image_root: Path) -> None:
    dataset = application.create_dataset(str(image_root), "sample")
    assert application.get_dataset(dataset["dataset_id"])["deleted_at"] is None

    deleted = application.delete_dataset(dataset["dataset_id"])
    assert deleted["deleted_at"] is not None
    assert application.list_datasets()["count"] == 0
    assert application.list_datasets(include_deleted=True)["count"] == 1

    restored = application.restore_dataset(dataset["dataset_id"])
    assert restored["deleted_at"] is None


def test_category_batch_is_atomic_on_name_conflict(application: Application, image_root: Path) -> None:
    dataset = application.create_dataset(str(image_root), "sample")
    with pytest.raises(DomainError) as captured:
        application.add_categories(
            dataset["dataset_id"],
            [CategoryCreate(name="same"), CategoryCreate(name="same")],
        )
    assert captured.value.code is ErrorCode.CATEGORY_NAME_CONFLICT
    assert application.list_categories(dataset["dataset_id"])["count"] == 0


def test_category_restore_conflict_preserves_deleted_state(application: Application, image_root: Path) -> None:
    dataset = application.create_dataset(str(image_root), "sample")
    created = application.add_categories(
        dataset["dataset_id"],
        [CategoryCreate(name="first"), CategoryCreate(name="second")],
    )["categories"]
    first_id = created[0]["category_id"]
    application.delete_category(dataset["dataset_id"], first_id)

    with pytest.raises(DomainError) as captured:
        application.restore_category(dataset["dataset_id"], first_id, "second")
    assert captured.value.code is ErrorCode.CATEGORY_NAME_CONFLICT
    assert application.get_category(dataset["dataset_id"], first_id)["deleted_at"] is not None


def test_bbox_batch_rolls_back_on_invalid_geometry(application: Application, image_root: Path) -> None:
    dataset_id, category_id = _dataset_and_category(application, image_root)
    with pytest.raises(DomainError):
        application.add_bbox_annotations(
            dataset_id,
            "0.png",
            [
                BBoxCreate(category_id=category_id, bbox=[0.1, 0.1, 0.4, 0.4]),
                BBoxCreate(category_id=category_id, bbox=[0.8, 0.1, 0.4, 0.4]),
            ],
        )
    assert application.list_annotations(dataset_id)["count"] == 0


def test_deleted_category_annotations_are_hidden(application: Application, image_root: Path) -> None:
    dataset_id, category_id = _dataset_and_category(application, image_root)
    application.add_bbox_annotations(
        dataset_id,
        "0.png",
        [BBoxCreate(category_id=category_id, bbox=[0.1, 0.1, 0.4, 0.4])],
    )
    application.delete_category(dataset_id, category_id)
    assert application.list_annotations(dataset_id)["count"] == 0
    assert application.list_annotations(dataset_id, include_deleted_categories=True)["count"] == 1


def test_list_images_random_order_is_deterministic(application: Application, image_root: Path) -> None:
    dataset_id, _ = _dataset_and_category(application, image_root)
    first = application.list_images(dataset_id, order_by="random", random_seed=7)["images"]
    second = application.list_images(dataset_id, order_by="random", random_seed=7)["images"]
    assert first == second
    assert len(application.list_images(dataset_id, offset=2, max_results=2)["images"]) == 2


def test_image_path_traversal_is_rejected(application: Application, image_root: Path) -> None:
    dataset_id, _ = _dataset_and_category(application, image_root)
    with pytest.raises(DomainError) as captured:
        application.set_image_status(dataset_id, "../outside.png", ImageStatus.COMPLETED)
    assert captured.value.code is ErrorCode.PATH_OUTSIDE_DATASET_ROOT


def test_extended_export_includes_negative_and_rotated_samples(
    application: Application,
    image_root: Path,
    tmp_path: Path,
) -> None:
    dataset_id, category_id = _dataset_and_category(application, image_root)
    application.set_image_status(dataset_id, "0.png", ImageStatus.COMPLETED)
    application.set_image_status(dataset_id, "1.png", ImageStatus.COMPLETED)
    application.add_rotated_bbox_annotations(
        dataset_id,
        "1.png",
        [
            RotatedBBoxCreate(
                category_id=category_id,
                polygon=[0.2, 0.2, 0.8, 0.2, 0.8, 0.8, 0.2, 0.8],
            )
        ],
    )
    output = tmp_path / "metadata.jsonl"
    result = application.export_metadata_jsonl(dataset_id, str(output), ExportMode.EXTENDED)
    records = [json.loads(line) for line in output.read_text().splitlines()]

    assert result["exported_images"] == 2
    assert records[0]["objects"] == {"bbox": [], "category": [], "polygon": [], "polygon_category": []}
    assert len(records[1]["objects"]["polygon"]) == 1


def test_autotrain_export_requires_five_completed_images(
    application: Application,
    image_root: Path,
    tmp_path: Path,
) -> None:
    dataset_id, _ = _dataset_and_category(application, image_root)
    application.set_image_status(dataset_id, "0.png", ImageStatus.COMPLETED)
    with pytest.raises(DomainError) as captured:
        application.export_metadata_jsonl(dataset_id, str(tmp_path / "metadata.jsonl"))
    assert captured.value.code is ErrorCode.AUTOTRAIN_LAYOUT_INCOMPATIBLE


def test_export_recovers_stale_lock_and_rejects_active_writer(
    application: Application,
    image_root: Path,
    tmp_path: Path,
) -> None:
    dataset_id, _ = _dataset_and_category(application, image_root)
    application.set_image_status(dataset_id, "0.png", ImageStatus.COMPLETED)
    stale_output = tmp_path / "stale.jsonl"
    stale_output.with_name(f".{stale_output.name}.lock").write_text("stale")

    application.export_metadata_jsonl(dataset_id, str(stale_output), ExportMode.EXTENDED)

    locked_output = tmp_path / "locked.jsonl"
    lock = FileLock(locked_output.with_name(f".{locked_output.name}.lock"))
    with lock, pytest.raises(DomainError) as captured:
        application.export_metadata_jsonl(dataset_id, str(locked_output), ExportMode.EXTENDED)
    assert captured.value.code is ErrorCode.OUTPUT_ALREADY_EXISTS


def test_category_edit_restore_and_validation(application: Application, image_root: Path) -> None:
    dataset_id, category_id = _dataset_and_category(application, image_root)
    edited = application.edit_category(dataset_id, category_id, name="car", description="Updated")
    assert edited["name"] == "car"
    assert application.get_category(dataset_id, category_id)["description"] == "Updated"
    application.delete_category(dataset_id, category_id)
    assert application.list_categories(dataset_id)["count"] == 0
    assert application.list_categories(dataset_id, include_deleted=True)["count"] == 1
    assert application.restore_category(dataset_id, category_id, "vehicle")["deleted_at"] is None

    for operation in (
        lambda: application.add_categories(dataset_id, []),
        lambda: application.edit_category(dataset_id, category_id),
        lambda: application.edit_category(dataset_id, category_id, name=" "),
        lambda: application.restore_category(dataset_id, category_id, " "),
    ):
        with pytest.raises(DomainError) as captured:
            operation()
        assert captured.value.code is ErrorCode.INVALID_ARGUMENT


def test_annotation_full_lifecycle_and_filters(application: Application, image_root: Path) -> None:
    dataset = application.create_dataset(str(image_root))
    dataset_id = dataset["dataset_id"]
    categories = application.add_categories(
        dataset_id,
        [CategoryCreate(name="first"), CategoryCreate(name="second")],
    )["categories"]
    first_id, second_id = (category["category_id"] for category in categories)

    bbox = application.add_bbox_annotations(
        dataset_id,
        "0.png",
        [BBoxCreate(category_id=first_id, bbox=[0.1, 0.1, 0.4, 0.4])],
    )["annotations"][0]
    edited_bbox = application.edit_bbox_annotation(dataset_id, bbox["annotation_id"], second_id, [0.2, 0.2, 0.5, 0.5])
    assert edited_bbox["category_id"] == second_id
    assert edited_bbox["geometry"] == [0.2, 0.2, 0.5, 0.5]
    assert (
        application.edit_bbox_annotation(dataset_id, bbox["annotation_id"], bbox=[0.1, 0.1, 0.3, 0.3])["category_id"]
        == second_id
    )

    rotated = application.add_rotated_bbox_annotations(
        dataset_id,
        "0.png",
        [RotatedBBoxCreate(category_id=first_id, polygon=[0.2, 0.2, 0.8, 0.2, 0.8, 0.8, 0.2, 0.8])],
    )["annotations"][0]
    unchanged = application.edit_rotated_bbox_annotation(dataset_id, rotated["annotation_id"], category_id=second_id)
    assert unchanged["corrected"] is False
    changed = application.edit_rotated_bbox_annotation(
        dataset_id,
        rotated["annotation_id"],
        polygon=[0.2, 0.2, 0.8, 0.2, 0.8, 0.8, 0.2, 0.795],
    )
    assert changed["corrected"] is True

    listed = application.list_annotations(
        dataset_id,
        image_path="0.png",
        annotation_type="bbox",
        category_ids=[second_id],
        annotation_ids=[bbox["annotation_id"]],
        offset=0,
        max_results=1,
    )
    assert listed["count"] == 1

    preview, metadata = application.preview_annotations(dataset_id, "0.png", max_width=50, max_height=50)
    assert preview.startswith(b"\x89PNG")
    assert metadata["annotation_count"] == 2
    assert application.preview_image(dataset_id, "0.png", 1000, 1000)[1]["clamped"] is True

    assert application.delete_annotations(dataset_id, [bbox["annotation_id"]], AnnotationType.BBOX)["count"] == 1
    assert (
        application.delete_annotations(dataset_id, [rotated["annotation_id"]], AnnotationType.ROTATED_BBOX)["count"]
        == 1
    )
    assert application.list_annotations(dataset_id)["count"] == 0


def test_annotation_and_listing_argument_validation(application: Application, image_root: Path) -> None:
    dataset_id, _ = _dataset_and_category(application, image_root)
    operations = (
        lambda: application.list_images(dataset_id, status="unknown"),
        lambda: application.list_images(dataset_id, order_by="size"),
        lambda: application.list_images(dataset_id, offset=-1),
        lambda: application.add_bbox_annotations(dataset_id, "0.png", []),
        lambda: application.add_rotated_bbox_annotations(dataset_id, "0.png", []),
        lambda: application.edit_bbox_annotation(dataset_id, 1),
        lambda: application.edit_rotated_bbox_annotation(dataset_id, 1),
        lambda: application.delete_annotations(dataset_id, [], AnnotationType.BBOX),
        lambda: application.list_annotations(dataset_id, annotation_type="polygon"),
        lambda: application.list_annotations(dataset_id, max_results=0),
        lambda: application.preview_image(dataset_id, "0.png", 0, 1),
        lambda: application.preview_annotations(dataset_id, "0.png", max_width=0),
    )
    for operation in operations:
        with pytest.raises(DomainError) as captured:
            operation()
        assert captured.value.code is ErrorCode.INVALID_ARGUMENT


def test_image_status_filter_and_successful_autotrain_export(
    application: Application,
    image_root: Path,
    tmp_path: Path,
) -> None:
    dataset_id, category_id = _dataset_and_category(application, image_root)
    for index in range(5):
        application.set_image_status(dataset_id, f"{index}.png", ImageStatus.COMPLETED)
    assert application.list_images(dataset_id, status="completed")["count"] == 5
    application.add_bbox_annotations(
        dataset_id,
        "0.png",
        [BBoxCreate(category_id=category_id, bbox=[0.1, 0.1, 0.4, 0.4])],
    )
    application.add_rotated_bbox_annotations(
        dataset_id,
        "0.png",
        [RotatedBBoxCreate(category_id=category_id, polygon=[0.2, 0.2, 0.8, 0.2, 0.8, 0.8, 0.2, 0.8])],
    )
    output = tmp_path / "autotrain.jsonl"
    result = application.export_metadata_jsonl(dataset_id, str(output), overwrite=True)
    assert result["exported_images"] == 5
    assert result["ignored_rotated_annotations"] == 1
    with pytest.raises(DomainError) as captured:
        application.export_metadata_jsonl(dataset_id, str(output))
    assert captured.value.code is ErrorCode.OUTPUT_ALREADY_EXISTS
