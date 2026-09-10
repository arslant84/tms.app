"""
ERD fix roadmap, Phase 3 (docs/erd-fix-roadmap.md, Issue 11).

Makes TravelRequest.created_by NOT NULL. Deferred until a production data
check confirmed there were zero NULL rows there (dev had already been
clean) - not something to guess at from dev data alone. `perform_create`
in trf/travel_request_views.py always sets this from the authenticated
user, so nullability was legacy caution rather than a real, currently-used
state.
"""

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("trf", "0016_add_updated_at_to_trfapprovalstep"),
    ]

    operations = [
        migrations.AlterField(
            model_name="travelrequest",
            name="created_by",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name="travel_requests_created",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
