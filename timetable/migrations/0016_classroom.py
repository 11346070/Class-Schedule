from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("timetable", "0015_teacher"),
    ]

    operations = [
        migrations.CreateModel(
            name="Classroom",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=50, unique=True, verbose_name="教室名稱")),
            ],
            options={
                "verbose_name": "教室",
                "verbose_name_plural": "教室",
                "ordering": ["name"],
            },
        ),
        migrations.AddField(
            model_name="course",
            name="classroom",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="courses",
                to="timetable.classroom",
                verbose_name="教室",
            ),
        ),
    ]
