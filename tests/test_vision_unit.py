"""Pruebas unitarias del módulo de visión (sin Django ni modelos ONNX)."""

import numpy as np
import pytest

from asistencia.tracker import ConfirmationTracker
from vision import annotator, codec, preprocessing
from vision.detector import FaceDetector, crop
from vision.pipeline import FaceResult, FrameAnalysis, RenderOptions, render
from vision.recognizer import (
    EMPTY_GALLERY, Match, build_gallery, from_bytes, match, normalize, to_bytes,
)

from .conftest import make_jpeg

pytestmark = pytest.mark.unit


# --- codec ----------------------------------------------------------------

def test_decode_valid_jpeg_returns_bgr_matrix():
    image = codec.decode_image(make_jpeg(320, 240))
    assert image.shape == (240, 320, 3)


@pytest.mark.parametrize("data", [b"", b"no-es-una-imagen"])
def test_decode_rejects_empty_or_corrupt_data(data):
    with pytest.raises(codec.InvalidImageError):
        codec.decode_image(data)


def test_decode_rejects_oversized_payload():
    with pytest.raises(codec.InvalidImageError, match="tamaño"):
        codec.decode_image(b"0" * (codec.MAX_IMAGE_BYTES + 1))


def test_data_url_has_jpeg_prefix():
    image = np.zeros((10, 10, 3), dtype=np.uint8)
    assert codec.to_data_url(image).startswith("data:image/jpeg;base64,")


# --- preprocessing --------------------------------------------------------

def test_dark_image_is_detected_as_low_light_and_enhanced():
    dark = np.full((100, 100, 3), 30, dtype=np.uint8)
    dark[25:75, 25:75] = 60
    assert preprocessing.is_low_light(dark)
    enhanced = preprocessing.enhance_lighting(dark)
    assert enhanced.shape == dark.shape
    assert enhanced.std() > dark.std()  # CLAHE aumenta el contraste


def test_resize_keeps_small_images_and_shrinks_large_ones():
    small = np.zeros((100, 200, 3), dtype=np.uint8)
    big = np.zeros((1000, 2000, 3), dtype=np.uint8)
    assert preprocessing.resize_max_side(small, 960) is small
    assert preprocessing.resize_max_side(big, 960).shape[:2] == (480, 960)


def test_blurry_face_fails_quality_check():
    flat = np.full((112, 112, 3), 128, dtype=np.uint8)
    quality = preprocessing.assess_face_quality(flat)
    assert not quality.ok and "borrosa" in quality.reason


def test_sharp_well_lit_face_passes_quality_check():
    rng = np.random.default_rng(1)
    textured = rng.integers(60, 200, size=(112, 112, 3), dtype=np.uint8)
    quality = preprocessing.assess_face_quality(textured)
    assert quality.ok
    assert 0 <= quality.score <= 1


def test_dark_face_fails_quality_check():
    rng = np.random.default_rng(2)
    dark = rng.integers(0, 60, size=(112, 112, 3), dtype=np.uint8)
    quality = preprocessing.assess_face_quality(dark)
    assert not quality.ok and "oscuro" in quality.reason


def test_empty_face_fails_quality_check():
    assert not preprocessing.assess_face_quality(np.zeros((0, 0, 3), dtype=np.uint8)).ok


@pytest.mark.parametrize("mode", list(preprocessing.VIEW_FILTERS) + ["inexistente"])
def test_every_view_filter_returns_bgr_image_of_same_size(mode):
    image = np.random.default_rng(3).integers(0, 255, size=(60, 80, 3), dtype=np.uint8)
    output = preprocessing.apply_view_filter(image, mode)
    assert output.shape == image.shape


# --- recognizer -----------------------------------------------------------

def test_match_returns_unknown_for_empty_gallery():
    result = match(EMPTY_GALLERY, np.ones(128))
    assert result == Match(label=None, similarity=0.0)


def test_match_finds_closest_identity_above_threshold():
    rng = np.random.default_rng(4)
    ana, luis = rng.normal(size=128), rng.normal(size=128)
    gallery = build_gallery([(1, ana), (2, luis)])
    probe = ana + rng.normal(scale=0.1, size=128)
    result = match(gallery, probe, threshold=0.4)
    assert result.label == 1 and result.similarity > 0.9


def test_match_rejects_stranger_below_threshold():
    rng = np.random.default_rng(5)
    gallery = build_gallery([(1, rng.normal(size=128))])
    result = match(gallery, rng.normal(size=128), threshold=0.4)
    assert result.label is None and not result.is_known


def test_embedding_bytes_roundtrip():
    vector = normalize(np.arange(128, dtype=np.float32))
    assert np.allclose(from_bytes(to_bytes(vector)), vector)


def test_from_bytes_rejects_wrong_dimension():
    with pytest.raises(ValueError):
        from_bytes(np.zeros(10, dtype=np.float32).tobytes())


# --- detector helpers -----------------------------------------------------

def test_crop_stays_inside_image():
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    assert crop(image, (80, 80, 40, 40), margin=0).shape[:2] == (20, 20)
    assert crop(image, (80, 80, 40, 40)).shape[:2] == (26, 26)  # margen 15 % = 6 px


def test_detection_row_is_clipped_to_frame():
    row = np.array([-5, -5, 50, 50] + [10] * 10 + [0.9], dtype=np.float32)
    detection = FaceDetector._to_detection(row, width=40, height=40)
    assert detection.box == (0, 0, 40, 40)
    assert detection.score == pytest.approx(0.9)


# --- annotator / render ---------------------------------------------------

def test_render_draws_annotations_and_pixelates_unknown_faces():
    rng = np.random.default_rng(6)
    image = rng.integers(0, 255, size=(240, 320, 3), dtype=np.uint8)
    unknown = FaceResult((40, 40, 80, 100), 0.9, ((60, 70),) * 5, Match(None, 0.1), image[:1, :1])
    known = FaceResult((180, 40, 80, 100), 0.9, ((200, 70),) * 5, Match(7, 0.8), image[:1, :1])
    analysis = FrameAnalysis(image, (unknown, known), low_light=True, elapsed_ms=12.0)
    output = render(analysis, {7: "Ana Pérez"},
                    RenderOptions(privacy=True, confirmed_labels=frozenset({7})))
    assert output.shape == image.shape
    assert not np.array_equal(output, image)
    assert analysis.unknown_count == 1 and len(analysis.known) == 1


def test_ascii_label_replaces_accents():
    assert annotator._ascii("José Muñoz") == "Jose Munoz"


# --- tracker --------------------------------------------------------------

class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_tracker_confirms_after_required_consecutive_hits():
    tracker = ConfirmationTracker(required_hits=3, window_seconds=2, clock=FakeClock())
    assert [tracker.observe(1, 10) for _ in range(4)] == [False, False, True, True]


def test_tracker_resets_streak_after_window_expires():
    clock = FakeClock()
    tracker = ConfirmationTracker(required_hits=2, window_seconds=1, clock=clock)
    tracker.observe(1, 10)
    clock.now = 5
    assert tracker.observe(1, 10) is False
    assert tracker.progress(1, 10) == 0.5
    clock.now = 10
    assert tracker.progress(1, 10) == 0.0


def test_tracker_keeps_sessions_independent_and_can_forget():
    tracker = ConfirmationTracker(required_hits=2, clock=FakeClock())
    tracker.observe(1, 10)
    tracker.observe(2, 10)
    tracker.forget_session(1)
    assert tracker.progress(1, 10) == 0.0
    assert tracker.progress(2, 10) == 0.5


def test_tracker_rejects_invalid_configuration():
    with pytest.raises(ValueError):
        ConfirmationTracker(required_hits=0)
