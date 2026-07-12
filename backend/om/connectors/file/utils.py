import os
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import IO

from om.configs.constants import DocumentSource
from om.configs.constants import FileOrigin
from om.connectors.cross_connector_utils.miscellaneous_utils import (
    process_onyx_metadata,
)
from om.connectors.models import Document
from om.connectors.models import ImageSection
from om.connectors.models import TextSection
from om.file_processing.extract_file_text import extract_text_and_images
from om.file_processing.extract_file_text import get_file_ext
from om.file_processing.file_types import OnyxFileExtensions
from om.file_processing.image_utils import store_image_and_create_section
from om.utils.logger import setup_logger


logger = setup_logger()


def _create_image_section(
    image_data: bytes,
    parent_file_name: str,
    display_name: str,
    media_type: str | None = None,
    link: str | None = None,
    idx: int = 0,
) -> tuple[ImageSection, str | None]:
    """
    Creates an ImageSection for an image file or embedded image.
    Stores the image in FileStore but does not generate a summary.

    Args:
        image_data: Raw image bytes
        parent_file_name: Name of the parent file (for embedded images)
        display_name: Display name for the image
        idx: Index for embedded images

    Returns:
        Tuple of (ImageSection, stored_file_name or None)
    """
    # Create a unique identifier for the image
    file_id = f"{parent_file_name}_embedded_{idx}" if idx > 0 else parent_file_name

    # Store the image and create a section
    try:
        section, stored_file_name = store_image_and_create_section(
            image_data=image_data,
            file_id=file_id,
            display_name=display_name,
            media_type=(
                media_type if media_type is not None else "application/octet-stream"
            ),
            link=link,
            file_origin=FileOrigin.CONNECTOR,
        )
        return section, stored_file_name
    except Exception as e:
        logger.error(f"Failed to store image {display_name}: {e}")
        raise e


def _process_file(
    file_id: str,
    file_name: str,
    file: IO[Any],
    metadata: dict[str, Any] | None,
    pdf_pass: str | None,
    file_type: str | None,
    default_source: DocumentSource = DocumentSource.FILE,
    doc_id_prefix: str = "FILE_CONNECTOR__",
) -> list[Document]:
    """
    Process a file and return a list of Documents.
    For images, creates ImageSection objects without summarization.
    For documents with embedded images, extracts and stores the images.

    Args:
        file_id: Unique identifier for the file
        file_name: Display name of the file
        file: Binary file-like object
        metadata: Optional metadata dict
        pdf_pass: Optional PDF password
        file_type: MIME type of the file
        default_source: DocumentSource to use if not overridden by metadata
        doc_id_prefix: Prefix for auto-generated document IDs
    """
    if metadata is None:
        metadata = {}

    # Get file extension and determine file type
    extension = get_file_ext(file_name)

    if extension not in OnyxFileExtensions.ALL_ALLOWED_EXTENSIONS:
        logger.warning(
            f"Skipping file '{file_name}' with unrecognized extension '{extension}'"
        )
        return []

    # If a zip is uploaded with a metadata file, we can process it here
    onyx_metadata, custom_tags = process_onyx_metadata(metadata)
    file_display_name = onyx_metadata.file_display_name or os.path.basename(file_name)
    time_updated = onyx_metadata.doc_updated_at or datetime.now(timezone.utc)
    primary_owners = onyx_metadata.primary_owners
    secondary_owners = onyx_metadata.secondary_owners
    link = onyx_metadata.link

    # These metadata items are not settable by the user
    source_type = onyx_metadata.source_type or default_source

    doc_id = onyx_metadata.document_id or f"{doc_id_prefix}{file_id}"
    title = metadata.get("title") or file_display_name

    # 1) If the file itself is an image, handle that scenario quickly
    if extension in OnyxFileExtensions.IMAGE_EXTENSIONS:
        # Read the image data
        image_data = file.read()
        if not image_data:
            logger.warning(f"Empty image file: {file_name}")
            return []

        # Create an ImageSection for the image
        try:
            section, _ = _create_image_section(
                image_data=image_data,
                parent_file_name=file_id,
                display_name=title,
                media_type=file_type,
            )

            return [
                Document(
                    id=doc_id,
                    sections=[section],
                    source=source_type,
                    semantic_identifier=file_display_name,
                    title=title,
                    doc_updated_at=time_updated,
                    primary_owners=primary_owners,
                    secondary_owners=secondary_owners,
                    metadata=custom_tags,
                )
            ]
        except Exception as e:
            logger.error(f"Failed to process image file {file_name}: {e}")
            return []

    # 2) Otherwise: text-based approach. Possibly with embedded images.
    file.seek(0)

    # Extract text and images from the file
    extraction_result = extract_text_and_images(
        file=file,
        file_name=file_name,
        pdf_pass=pdf_pass,
        content_type=file_type,
    )

    # Each file may have file-specific ONYX_METADATA https://docs.onyx.app/admins/connectors/official/file
    # If so, we should add it to any metadata processed so far
    if extraction_result.metadata:
        logger.debug(
            f"Found file-specific metadata for {file_name}: {extraction_result.metadata}"
        )
        onyx_metadata, more_custom_tags = process_onyx_metadata(
            extraction_result.metadata
        )

        # Add file-specific tags
        custom_tags.update(more_custom_tags)

        # File-specific metadata overrides metadata processed so far
        source_type = onyx_metadata.source_type or source_type
        primary_owners = onyx_metadata.primary_owners or primary_owners
        secondary_owners = onyx_metadata.secondary_owners or secondary_owners
        time_updated = onyx_metadata.doc_updated_at or time_updated
        file_display_name = onyx_metadata.file_display_name or file_display_name
        title = onyx_metadata.title or onyx_metadata.file_display_name or title
        link = onyx_metadata.link or link

    # Build sections: first the text as a single Section
    sections: list[TextSection | ImageSection] = []
    if extraction_result.text_content.strip():
        logger.debug(f"Creating TextSection for {file_name} with link: {link}")
        sections.append(
            TextSection(link=link, text=extraction_result.text_content.strip())
        )

    # Then any extracted images from docx, PDFs, etc.
    for idx, (img_data, img_name) in enumerate(
        extraction_result.embedded_images, start=1
    ):
        # Store each embedded image as a separate file in FileStore
        # and create a section with the image reference
        try:
            image_section, stored_file_name = _create_image_section(
                image_data=img_data,
                parent_file_name=file_id,
                display_name=f"{title} - image {idx}",
                media_type="application/octet-stream",  # Default media type for embedded images
                idx=idx,
            )
            sections.append(image_section)
            logger.debug(
                f"Created ImageSection for embedded image {idx} "
                f"in {file_name}, stored as: {stored_file_name}"
            )
        except Exception as e:
            logger.warning(
                f"Failed to process embedded image {idx} in {file_name}: {e}"
            )

    return [
        Document(
            id=doc_id,
            sections=sections,
            source=source_type,
            semantic_identifier=file_display_name,
            title=title,
            doc_updated_at=time_updated,
            primary_owners=primary_owners,
            secondary_owners=secondary_owners,
            metadata=custom_tags,
        )
    ]
