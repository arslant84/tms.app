"""
Regression coverage for FileSizeValidationMiddleware's backup-restore
exemption. max_file_upload_size is sized for routine user uploads (profile
photos, passport scans); a real database backup already exceeds a low
setting value (reproduced live: 2.7 MB backup rejected against a 1 MB
setting), which made "Restore from Backup" in Django admin unusable.

Tests the middleware directly (bypassing the full request/response cycle -
it only inspects request.method/path/META before the body is ever parsed)
since Django's test client enforces that CONTENT_LENGTH match the actual
body bytes provided, which a synthetic oversized-upload test can't satisfy
without transferring real megabytes.
"""

import pytest
from accounts.models import ApplicationSetting
from django.test import RequestFactory
from tms_project.middleware import FileSizeValidationMiddleware


@pytest.fixture
def small_max_upload_setting(db):
    ApplicationSetting.set_setting(
        "max_file_upload_size", 1048576, setting_type="number"  # 1 MB
    )


def _make_middleware(called_flag):
    def get_response(request):
        called_flag["called"] = True
        return "ok"

    return FileSizeValidationMiddleware(get_response)


@pytest.mark.django_db
class TestFileSizeValidationMiddlewareBackupExemption:
    def test_restore_backup_endpoint_exempt_from_small_upload_limit(
        self, small_max_upload_setting
    ):
        request = RequestFactory().post("/admin/accounts/databasebackup/restore/")
        request.META["CONTENT_LENGTH"] = str(2 * 1024 * 1024)  # 2 MB, over the 1 MB cap

        called = {"called": False}
        middleware = _make_middleware(called)
        response = middleware(request)

        assert called["called"] is True
        assert response == "ok"

    def test_other_uploads_still_enforce_the_limit(self, small_max_upload_setting):
        request = RequestFactory().post("/api/some-upload-endpoint/")
        request.META["CONTENT_LENGTH"] = str(2 * 1024 * 1024)  # 2 MB, over the 1 MB cap

        called = {"called": False}
        middleware = _make_middleware(called)
        response = middleware(request)

        assert called["called"] is False
        assert response.status_code == 413
