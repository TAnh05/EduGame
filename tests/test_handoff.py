import unittest
from unittest.mock import Mock

from ocr_module.config import QualityGateConfig
from ocr_module.pipeline import OCRResult
from ocr_module.handoff import deliver_text


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.result = OCRResult(text="This is a valid paragraph for the game consumer.", ok=True)
        self.consumer = Mock()

    def send(self, **overrides):
        args = dict(result=self.result, text=self.result.text, consumer=self.consumer,
                    gate=QualityGateConfig(), reviewed=False,
                    result_context="file:config:page", current_context="file:config:page")
        args.update(overrides)
        return deliver_text(**args)

    def test_consumer_receives_plain_string(self):
        self.send()
        self.consumer.assert_called_once_with(self.result.text)

    def test_empty_or_rejected_text_never_delivered(self):
        for text in ("", "  ", "short", "alpha beta gamma delta " * 20):
            with self.subTest(text=text[:20]), self.assertRaises(ValueError):
                self.send(text=text, reviewed=True)
        self.consumer.assert_not_called()

    def test_failed_ocr_and_edits_require_review(self):
        self.result.ok = False
        with self.assertRaises(ValueError):
            self.send()
        self.send(reviewed=True)
        self.consumer.reset_mock()
        self.result.ok = True
        with self.assertRaises(ValueError):
            self.send(text="This is the corrected text for the game.")
        self.send(text="This is the corrected text for the game.", reviewed=True)
        self.consumer.assert_called_once_with("This is the corrected text for the game.")

    def test_stale_or_missing_provenance_blocked(self):
        for context in ("new-file", "new-config", "new-rotation", "new-pdf-range", ""):
            with self.subTest(context=context), self.assertRaises(ValueError):
                self.send(current_context=context)
        self.consumer.assert_not_called()

    def test_missing_or_failing_consumer_does_not_report_success(self):
        with self.assertRaises(ValueError):
            self.send(consumer=None)
        self.consumer.side_effect = RuntimeError("consumer unavailable")
        with self.assertRaises(RuntimeError):
            self.send()
