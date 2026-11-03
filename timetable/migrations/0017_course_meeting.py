from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("timetable", "0016_classroom"),
    ]

    operations = [
        migrations.CreateModel(
            name="CourseMeeting",
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
                ("weekday", models.PositiveSmallIntegerField(verbose_name="星期")),
                ("start_period", models.PositiveSmallIntegerField(verbose_name="開始節次")),
                ("end_period", models.PositiveSmallIntegerField(verbose_name="結束節次")),
                (
                    "classroom",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="extra_meetings",
                        to="timetable.classroom",
                        verbose_name="教室",
                    ),
                ),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="extra_meetings",
                        to="timetable.course",
                        verbose_name="課程",
                    ),
                ),
            ],
            options={
                "verbose_name": "其他上課時段",
                "verbose_name_plural": "其他上課時段",
                "ordering": ["weekday", "start_period"],
            },
        ),
    ]
