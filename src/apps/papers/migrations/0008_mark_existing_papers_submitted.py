from django.db import migrations


def mark_existing_papers_submitted(apps, schema_editor):
    Paper = apps.get_model('papers', 'Paper')
    Paper.objects.filter(
        submission__isnull=False,
        status='draft',
    ).distinct().update(status='submitted')


class Migration(migrations.Migration):
    dependencies = [
        ('papers', '0007_submission_version_required'),
    ]

    operations = [
        migrations.RunPython(
            mark_existing_papers_submitted,
            migrations.RunPython.noop,
        ),
    ]
