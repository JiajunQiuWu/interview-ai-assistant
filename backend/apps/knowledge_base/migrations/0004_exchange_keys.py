import uuid

from django.db import migrations, models

MODEL_NAMES = (
    "Category",
    "Question",
    "Answer",
    "QuestionVariant",
    "Tag",
    "ProfessionalExperience",
)


def populate_exchange_keys(apps, schema_editor):
    database = schema_editor.connection.alias
    for model_name in MODEL_NAMES:
        model = apps.get_model("knowledge_base", model_name)
        manager = model.objects.using(database)
        primary_keys = manager.filter(exchange_key__isnull=True).values_list(
            "pk", flat=True
        )
        for primary_key in primary_keys.iterator():
            manager.filter(pk=primary_key).update(exchange_key=uuid.uuid4())


class Migration(migrations.Migration):
    dependencies = [
        (
            "knowledge_base",
            "0003_remove_question_answer_tag_question_tags_answer_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="exchange_key",
            field=models.UUIDField(
                editable=False,
                null=True,
                verbose_name="clave de intercambio",
            ),
        ),
        migrations.AddField(
            model_name="question",
            name="exchange_key",
            field=models.UUIDField(
                editable=False,
                null=True,
                verbose_name="clave de intercambio",
            ),
        ),
        migrations.AddField(
            model_name="answer",
            name="exchange_key",
            field=models.UUIDField(
                editable=False,
                null=True,
                verbose_name="clave de intercambio",
            ),
        ),
        migrations.AddField(
            model_name="questionvariant",
            name="exchange_key",
            field=models.UUIDField(
                editable=False,
                null=True,
                verbose_name="clave de intercambio",
            ),
        ),
        migrations.AddField(
            model_name="tag",
            name="exchange_key",
            field=models.UUIDField(
                editable=False,
                null=True,
                verbose_name="clave de intercambio",
            ),
        ),
        migrations.AddField(
            model_name="professionalexperience",
            name="exchange_key",
            field=models.UUIDField(
                editable=False,
                null=True,
                verbose_name="clave de intercambio",
            ),
        ),
        migrations.RunPython(populate_exchange_keys, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="category",
            name="exchange_key",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                unique=True,
                verbose_name="clave de intercambio",
            ),
        ),
        migrations.AlterField(
            model_name="question",
            name="exchange_key",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                unique=True,
                verbose_name="clave de intercambio",
            ),
        ),
        migrations.AlterField(
            model_name="answer",
            name="exchange_key",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                unique=True,
                verbose_name="clave de intercambio",
            ),
        ),
        migrations.AlterField(
            model_name="questionvariant",
            name="exchange_key",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                unique=True,
                verbose_name="clave de intercambio",
            ),
        ),
        migrations.AlterField(
            model_name="tag",
            name="exchange_key",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                unique=True,
                verbose_name="clave de intercambio",
            ),
        ),
        migrations.AlterField(
            model_name="professionalexperience",
            name="exchange_key",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                unique=True,
                verbose_name="clave de intercambio",
            ),
        ),
    ]
