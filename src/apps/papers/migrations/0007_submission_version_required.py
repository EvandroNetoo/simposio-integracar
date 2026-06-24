from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('papers', '0006_alter_submission_options_paper_status_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submission',
            name='version',
            field=models.PositiveIntegerField(
                editable=False,
                verbose_name='versão',
            ),
        ),
    ]
