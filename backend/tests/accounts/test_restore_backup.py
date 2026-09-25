"""
Regression coverage for the pg_restore invocation in
AdminActionLogAdmin/DatabaseBackupAdmin.restore_backup_view.

Restoring a dump created under one DB role (e.g. postgres) while connected
as a different, non-superuser app role (e.g. omega) fails on the dump's
ownership/ACL statements - "must be member of role X" - even though the
actual data restores fine. Reproduced live. Fix: pass --no-owner
--no-privileges so pg_restore skips replaying those statements; the
target database's real grants are already correct independently of the
dump.
"""

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from accounts.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse


@pytest.fixture
def superuser(db):
    return User.objects.create_user(
        email="restore-test-admin@example.com",
        password="Test1234!Test",
        name="Restore Test Admin",
        is_superuser=True,
        is_staff=True,
        is_active=True,
    )


@pytest.mark.django_db
class TestRestoreBackupPgRestoreFlags:
    def test_pg_restore_called_with_no_owner_and_no_privileges(self, client, superuser):
        client.force_login(superuser)
        url = reverse("admin:accounts_restore_backup")
        upload = SimpleUploadedFile("test.dump", BytesIO(b"fake dump content").read())

        with patch("accounts.admin.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            client.post(url, {"backup_file": upload, "confirm": "on"})

        # Second call is pg_restore (first is the pre-restore pg_dump snapshot).
        assert mock_run.call_count == 2
        pg_restore_args = mock_run.call_args_list[1].args[0]
        assert "--no-owner" in pg_restore_args
        assert "--no-privileges" in pg_restore_args
