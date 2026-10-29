import asyncio
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile

from app.api.v1.routers import product


def test_save_product_image_rejects_unsupported_content_type() -> None:
    upload = UploadFile(
        filename="not-an-image.svg",
        file=BytesIO(b"<svg></svg>"),
        headers={"content-type": "image/svg+xml"},
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(product.save_product_image(upload))

    assert exc.value.status_code == 415


def test_save_product_image_rejects_content_that_does_not_match_mime_type() -> None:
    upload = UploadFile(
        filename="fake.jpg",
        file=BytesIO(b"not really a jpeg"),
        headers={"content-type": "image/jpeg"},
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(product.save_product_image(upload))

    assert exc.value.status_code == 415


def test_save_product_image_persists_random_filename_and_public_path(
    tmp_path, monkeypatch
) -> None:
    image_bytes = b"\xff\xd8\xff\xe0test-image-content"
    monkeypatch.setattr(product, "PRODUCT_IMAGES_DIR", tmp_path)
    upload = UploadFile(
        filename="../../tomato.jpg",
        file=BytesIO(image_bytes),
        headers={"content-type": "image/jpeg"},
    )

    image_path = asyncio.run(product.save_product_image(upload))

    filename = image_path.rsplit("/", maxsplit=1)[-1]
    assert image_path.startswith("/media/products/")
    assert filename != "tomato.jpg"
    assert (tmp_path / filename).read_bytes() == image_bytes
